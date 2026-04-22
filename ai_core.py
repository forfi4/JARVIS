import base64
import json
import re
import time
import io
import pyautogui
import pyperclip
from openai import OpenAI
from groq import Groq

import config
from memory_manager import (
    load_memory,
    summarize_chat_history_if_needed,
    append_to_chat_log
)

# --- Client Initialization ---
client = Groq(api_key=config.GROQ_API_KEY)
or_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=config.OPENROUTER_API_KEY,
)

chat_history = []

# ============================================================
# NEW FEATURE: Improved Model Priority Chain
# Models are tried in order; exhausted models are skipped for the day.
# ============================================================

# (provider, model_name, supports_json_mode)
MODEL_CHAIN = [
    ("groq",       "llama-3.3-70b-versatile",                      True),
    ("groq",       "llama-3.1-8b-instant",                         True),
    ("openrouter", "nousresearch/hermes-3-llama-3.1-405b:free",    False),
    ("openrouter", "google/gemma-3-12b-it:free",                   False),
    ("openrouter", "meta-llama/llama-3.2-3b-instruct:free",        False),
]

def _call_model(provider, model, messages, max_tokens, temperature, json_mode=False):
    """Helper — calls the right client and returns the response text."""
    kwargs = dict(model=model, messages=messages, max_tokens=max_tokens, temperature=temperature)
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if provider == "groq":
        resp = client.chat.completions.create(**kwargs)
    else:
        resp = or_client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


def generate_text(prompt, max_tokens=8000, temperature=0.7):
    """
    Generate text using the model priority chain.
    Automatically skips exhausted models and saves new exhaustions.
    """
    from memory_manager import save_exhausted_models
    messages = [{"role": "user", "content": prompt}]
    
    for provider, model, _ in MODEL_CHAIN:
        if model in config.EXHAUSTED_DAILY_MODELS:
            print(f"[MODEL] Skipping exhausted: {model}")
            continue
        try:
            print(f"[MODEL] Trying {model}...")
            result = _call_model(provider, model, messages, max_tokens, temperature)
            if result:
                return result
        except Exception as e:
            err = str(e).lower()
            if any(k in err for k in ["rate limit", "quota", "exhausted", "limit reached", "429"]):
                config.EXHAUSTED_DAILY_MODELS.add(model)
                save_exhausted_models(config.EXHAUSTED_DAILY_MODELS)
                print(f"[MODEL] {model} rate-limited → skipping for today.")
            else:
                print(f"[MODEL] {model} error: {e}")
    
    print("[MODEL] ⚠️ All models failed.")
    return None


# ============================================================
# ORIGINAL: Text Cleaning Utilities
# ============================================================

def clean_repetitive_content(content):
    """Removes duplicate paragraphs, sentences, and headers (including '(continued)' variants)"""
    paragraphs = content.split('\n')
    cleaned = []
    seen_paragraphs = set()
    seen_headers = set()
    
    for para in paragraphs:
        stripped = para.strip()
        if not stripped:
            cleaned.append(para)
            continue
        
        if stripped.startswith("##") or stripped.startswith("# "):
            clean_header = re.sub(r'\s*\(continued\)', '', stripped, flags=re.IGNORECASE).strip()
            clean_header = re.sub(r'\s*\(המשך\)', '', clean_header, flags=re.IGNORECASE).strip()
            header_text = clean_header.lstrip('#').strip()
            header_fp = header_text[:50].lower()
            if header_fp in seen_headers:
                continue
            seen_headers.add(header_fp)
            cleaned.append(clean_header)
            continue
        
        fingerprint = stripped[:60]
        if fingerprint in seen_paragraphs:
            continue
        seen_paragraphs.add(fingerprint)
        
        sentences = re.split(r'(?<=[.!?])\s+', stripped)
        seen_sentences = set()
        unique_sentences = []
        for sentence in sentences:
            sent_fp = sentence[:40]
            if sent_fp not in seen_sentences:
                seen_sentences.add(sent_fp)
                unique_sentences.append(sentence)
        
        cleaned_para = ' '.join(unique_sentences)
        if len(cleaned_para) > 30:
            cleaned.append(cleaned_para)
    
    return '\n'.join(cleaned)


def clean_ai_meta_text(content):
    """Removes AI meta-commentary, English notes, and instruction leaks"""
    lines = content.split('\n')
    cleaned_lines = []
    skip_mode = False
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if not skip_mode:
                cleaned_lines.append(line)
            continue
        
        if stripped.startswith("##") or stripped.startswith("# "):
            clean_line = re.sub(r'\s*\(continued\)', '', line, flags=re.IGNORECASE).strip()
            clean_line = re.sub(r'\s*\(המשך\)', '', clean_line, flags=re.IGNORECASE).strip()
            cleaned_lines.append(clean_line)
            skip_mode = False
            continue
        
        if re.match(r'^(Notes|Potential|Improvements|Let me know|I hope|Here\'s|Here are|Please note|Important)', stripped, re.IGNORECASE):
            skip_mode = True
            continue
        
        if skip_mode:
            if re.search(r'[\u0590-\u05ea]', stripped) and len(stripped) > 30:
                skip_mode = False
            else:
                continue
        
        has_hebrew = bool(re.search(r'[\u0590-\u05ea]', stripped))
        if not has_hebrew:
            meta_patterns = [
                r'^(Okay|Sure|Certainly|Of course|Here|I\'ll|I\'ve|I will|I have|Let me|Please|Note:|Warning:)',
                r'(follow|instruction|anti-repetition|as requested|you asked|clarification)',
                r'^\*\s+', r'^-\s+\w+:',
            ]
            if any(re.search(p, stripped, re.IGNORECASE) for p in meta_patterns):
                continue
            if len(stripped) > 100 and not stripped.startswith("##"):
                continue
        
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


# ============================================================
# UPDATED: analyze_command_with_ai — adds new intents + chat logging + summarization
# ============================================================

def analyze_command_with_ai(command):
    global chat_history
    
    # NEW: Auto-summarize if history is getting long
    chat_history = summarize_chat_history_if_needed(chat_history, generate_text)
    
    # Load long-term memory
    current_memories = load_memory()
    memory_context = ""
    if current_memories:
        memory_context = (
            f"CRITICAL FACTS TO REMEMBER ABOUT THE USER {config.USER_NAME}:\n"
            + "\n".join([f"- {m}" for m in current_memories])
            + "\n\n"
        )

    system_prompt = f"""
{memory_context}You are Jarvis, a highly intelligent AI assistant. You are currently talking to your boss and creator, {config.USER_NAME}.
Analyze the user's command and return ONLY a valid JSON object. Do not add markdown or text outside the JSON.

The JSON must have this exact structure:
{{
    "intent": "MUST BE EXACTLY ONE OF: [send_whatsapp, download_media, open_app, generate_doc, generate_ppt, close_app, open_website, play_youtube, search_google, get_weather_global, take_screenshot, handle_screenshot, type_text, fix_language, set_volume, set_timer, open_camera, lock_pc, add_todo, clear_todo, standby, shutdown, get_time, vision_analyze, web_research, general_chat, press_key, scroll, system_status, media_control, play_spotify, remember_fact, identify_and_play, set_reminder, run_code, read_email, send_email, show_chat_log]",
    "target": "Depends on intent — see rules below. Otherwise empty string.",
    "value": "Depends on intent — see rules below. Otherwise 0.",
    "response": "A short, witty response in the EXACT SAME LANGUAGE as the user's command. Use CRITICAL FACTS if relevant. Do NOT hallucinate words."
}}

INTENT RULES (original):
- send_whatsapp → target=contact name, value=message text
- download_media → target=search query, value=media type
- open_app / close_app → target=app name
- generate_doc / generate_ppt → target=topic
- open_website → target=URL
- play_youtube → target=search query
- search_google → target=query (ONLY when user says "open google" / "search in google")
- get_weather_global → target=city name in English
- take_screenshot → target/value empty
- handle_screenshot → target='desktop', 'downloads', or 'clipboard'
- type_text → target/value empty
- fix_language → target/value empty
- set_volume → value=0-100 (specific), -1 (down), -2 (up)
- set_timer → value=seconds as integer
- press_key → target=key name
- scroll → target='up' or 'down'
- media_control → target='playpause', 'nexttrack', or 'prevtrack'
- play_spotify → target=song/action, value=type
- remember_fact → value=the exact fact to remember
- identify_and_play → target='song_recognition'
- web_research → target=the search query or topic
- vision_analyze → target/value empty

NEW INTENT RULES:
- set_reminder → target=reminder text (what to remind), value=time string like '5 minutes', '2 hours', 'tomorrow 9am'
- run_code → target=short description of what to do, value=Python code if user provided it (else empty)
- read_email → target=empty, value=0
- send_email → target=recipient (email address or name), value=subject|body (pipe-separated)
- show_chat_log → target=empty, value=0 (user wants to see/hear recent conversation)

CRITICAL RULES:
- identify_and_play → ONLY when user asks to identify/recognize/find a song they are singing or playing
- remember_fact → ONLY when user EXPLICITLY says to remember something
- play_spotify → ONLY for explicit Spotify requests
- media_control → ONLY for controlling already-playing media
- web_research → facts, recipes, news, summaries, general knowledge
- Return ONLY valid JSON. No markdown. No extra text.
"""

    # Log user command to chat log
    append_to_chat_log("user", command)
    
    chat_history.append({"role": "user", "content": command})
    if len(chat_history) > 10:
        chat_history = chat_history[-10:]
    
    messages = [{"role": "system", "content": system_prompt}] + chat_history

    # Try Groq models first (JSON mode supported)
    for provider, model, supports_json in MODEL_CHAIN[:2]:
        if model in config.EXHAUSTED_DAILY_MODELS:
            continue
        try:
            result = _call_model(provider, model, messages, 1000, 0.3, json_mode=supports_json)
            parsed = json.loads(result)
            print(f"\n[AI DECISION] Intent: {parsed.get('intent')} | Response: {parsed.get('response')}\n")
            
            response_text = parsed.get("response", "")
            chat_history.append({"role": "assistant", "content": response_text})
            
            # Log Jarvis response to chat log
            if response_text:
                append_to_chat_log("jarvis", response_text)
            
            return parsed
        except Exception as e:
            err = str(e).lower()
            if any(k in err for k in ["rate limit", "quota", "429"]):
                config.EXHAUSTED_DAILY_MODELS.add(model)
                from memory_manager import save_exhausted_models
                save_exhausted_models(config.EXHAUSTED_DAILY_MODELS)
            print(f"[ROUTER] {model} failed: {e}")
    
    return {"intent": "general_chat", "target": "", "value": 0,
            "response": "יש לי בעיה בחיבור לשרת אדוני." }


# ============================================================
# ORIGINAL + IMPROVED: Vision Analysis
# NEW: Also supports analyzing the screen (not just camera)
# ============================================================

def analyze_image_with_ai(prompt, b64_image):
    """Analyze an image using vision model. Falls back to OpenRouter if Groq fails."""
    try:
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": f"You are Jarvis. Reply ONLY in the user's language. Be concise. User asked: '{prompt}'"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
            ]}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"[VISION] Groq failed: {e}. Trying OpenRouter...")
        try:
            completion = or_client.chat.completions.create(
                model="google/gemini-flash-1.5",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": f"You are Jarvis. Be concise. User asked: '{prompt}'"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                ]}]
            )
            return completion.choices[0].message.content
        except Exception as e2:
            print(f"[VISION] OpenRouter also failed: {e2}")
            return "סליחה אדוני, הייתה שגיאה בניתוח התמונה."


def analyze_screen_with_ai(prompt):
    """
    NEW FEATURE: Capture the current screen and analyze it with AI.
    Useful for: 'what does my screen show?', 'read the error on screen', etc.
    """
    try:
        screenshot = pyautogui.screenshot()
        screenshot = screenshot.resize((1280, 720))  # Resize to save tokens
        buffer = io.BytesIO()
        screenshot.save(buffer, format='JPEG', quality=75)
        b64_img = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return analyze_image_with_ai(prompt, b64_img)
    except Exception as e:
        print(f"[VISION] Screen capture error: {e}")
        return "לא הצלחתי לצלם את המסך." if any('\u0590' <= c <= '\u05ea' for c in prompt) else "Failed to capture screen."


# ============================================================
# ORIGINAL: Language Fix
# ============================================================

def fix_language_gibberish():
    """Fix Hebrew/English keyboard layout mix-up in the focused text field"""
    try:
        pyautogui.click()
        time.sleep(0.2)
        pyperclip.copy('')
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.2)
        pyautogui.hotkey('ctrl', 'x')
        time.sleep(0.3)
        
        gibberish = pyperclip.paste().strip()
        if not gibberish:
            time.sleep(0.2)
            gibberish = pyperclip.paste().strip()
            if not gibberish:
                return False

        eng_to_heb = {
            'q': '/', 'w': "'", 'e': 'ק', 'r': 'ר', 't': 'א', 'y': 'ט', 'u': 'ו', 'i': 'ן',
            'o': 'ם', 'p': 'פ', 'a': 'ש', 's': 'ד', 'd': 'ג', 'f': 'כ', 'g': 'ע', 'h': 'י',
            'j': 'ח', 'k': 'ל', 'l': 'ך', ';': 'ף', "'": ',', 'z': 'ז', 'x': 'ס', 'c': 'ב',
            'v': 'ה', 'b': 'נ', 'n': 'מ', 'm': 'צ', ',': 'ת', '.': 'ץ', '/': '.', ' ': ' '
        }
        heb_to_eng = {v: k for k, v in eng_to_heb.items()}

        if any('a' <= char.lower() <= 'z' for char in gibberish):
            fixed_text = "".join(eng_to_heb.get(char.lower(), char) for char in gibberish)
        else:
            fixed_text = "".join(heb_to_eng.get(char, char) for char in gibberish)

        pyperclip.copy(fixed_text)
        time.sleep(0.2)
        pyautogui.hotkey('ctrl', 'v')
        return True
        
    except Exception as e:
        print(f"[LANG] fix_language error: {e}")
        return False