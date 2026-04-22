from setup_wizard import run_if_needed
run_if_needed()
import os
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"
import pyautogui
import sys
import pygame
import subprocess
import datetime
import time
import pywhatkit
from AppOpener import open as open_app, close as close_app
import requests
import psutil
import re
import threading
import audio_engine
import math
import random
import customtkinter as ct
import webbrowser
import ctypes
import cv2
from dotenv import load_dotenv
from PIL import Image
import urllib.request
import xml.etree.ElementTree as ET
import base64
from bidi.algorithm import get_display
import textwrap
import json
import urllib.parse
import shutil
import pyperclip
from playwright.sync_api import sync_playwright
from docx import Document
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from openai import OpenAI
import keyboard
from duckduckgo_search import DDGS
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
import yt_dlp
from shazamio import Shazam
import asyncio
from system_utils import *
from memory_manager import *
from skills import *
from audio_engine import *
from ai_core import *
from gui import *





# ============================================================
# ORIGINAL: Contacts
# ============================================================
CONTACTS = {
    "אמא": "+972535705052",
    "אבא": "+972529270383",
    "רום": "+972581234567"
}

# ============================================================
# NEW FEATURE 1: Global Hotkey — Press Ctrl+J anywhere to wake Jarvis
# No need to say the wake word — just press the shortcut!
# ============================================================

def _setup_hotkey():
    """
    Register Ctrl+J as a global hotkey to force-wake Jarvis from anywhere.
    Works even when other windows are in focus.
    """
    def _on_hotkey():
        config.hotkey_wake_trigger = True
        print("[HOTKEY] Ctrl+J pressed — forcing Jarvis awake!")
    
    try:
        keyboard.add_hotkey('ctrl+j', _on_hotkey)
        print("[HOTKEY] Ctrl+J registered — press it anywhere to wake Jarvis.")
    except Exception as e:
        print(f"[HOTKEY] Could not register hotkey: {e}")

# ============================================================
# NEW FEATURE 2: Proactive System Alerts
# Jarvis monitors CPU/RAM and warns you if things get critical.
# Also announces when reminders are about to fire.
# ============================================================

def _proactive_alerts_loop():
    """
    Background thread that monitors system health and speaks
    proactive warnings. Runs every 60 seconds.
    """
    cpu_warned = False
    ram_warned = False
    
    while True:
        try:
            time.sleep(60)
            
            # High CPU warning
            cpu = psutil.cpu_percent(interval=2)
            if cpu > 90 and not cpu_warned:
                speak(f"Warning, sir. CPU usage is critically high at {int(cpu)} percent.")
                cpu_warned = True
            elif cpu < 75:
                cpu_warned = False
            
            # High RAM warning
            ram = psutil.virtual_memory().percent
            if ram > 90 and not ram_warned:
                speak(f"Warning, sir. RAM usage is at {int(ram)} percent. You may want to close some applications.")
                ram_warned = True
            elif ram < 80:
                ram_warned = False
                
        except Exception as e:
            print(f"[ALERTS] Error: {e}")

# ============================================================
# NEW FEATURE 3: Watchdog — Auto-restarts brain if it crashes
# If jarvis_brain() throws an unhandled exception, the watchdog
# detects it and restarts the thread automatically.
# ============================================================

_brain_crash_count = 0

def _watchdog_loop():
    """
    Monitors the brain thread and restarts it if it dies.
    Gives up after 5 consecutive crashes to avoid infinite restart loops.
    """
    global brain_thread, _brain_crash_count
    
    while True:
        time.sleep(5)
        try:
            if not brain_thread.is_alive():
                _brain_crash_count += 1
                if _brain_crash_count > 5:
                    print(f"[WATCHDOG] ⚠️ Brain crashed {_brain_crash_count} times. Giving up.")
                    speak("Sir, I've experienced too many crashes. Please restart me manually.")
                    break
                
                print(f"[WATCHDOG] 🔄 Brain thread died! Restarting... (attempt {_brain_crash_count})")
                speak("Systems restarting, sir. One moment.")
                
                brain_thread = threading.Thread(
                    target=jarvis_brain, daemon=True, name="JarvisBrain"
                )
                brain_thread.start()
                time.sleep(3)
            else:
                _brain_crash_count = 0  # Reset counter on healthy check
        except Exception as e:
            print(f"[WATCHDOG] Error: {e}")

# ============================================================
# ORIGINAL + EXTENDED: Jarvis Brain (main command loop)
# ============================================================

def jarvis_brain():
    global jarvis_state, todo_list, todo_updated, cap
    is_awake = False
    morning_briefing()

    while True:
        # ── NEW: Check hotkey trigger ──────────────────────────
        if config.hotkey_wake_trigger:
            config.hotkey_wake_trigger = False
            is_awake = True
            speak("Yes sir, I'm listening.")
            continue
        # ──────────────────────────────────────────────────────

        # ── NEW: Porcupine wake word (if configured) ────────────
        # When PORCUPINE_KEY is set, use always-on offline detection
        # instead of sending silence to Whisper every 3 seconds.
        if not is_awake and audio_engine._porcupine_available:
            detected = audio_engine._porcupine_listen_for_wake()
            if detected:
                is_awake = True
                speak("Yes sir?")
            continue
        # ──────────────────────────────────────────────────────

        text = listen(is_awake)
        if not text:
            continue

        command = ""
        if not is_awake:
            wake_words = ["jarvis", "ג'רוויס", "גרוויס", "ג'ארביס", "גארביס"]
            if any(w in text for w in wake_words):
                is_awake = True
                command = text
                for w in wake_words:
                    command = command.replace(w, "")
                command = command.strip(" .,!?")
                if not command:
                    if any('\u0590' <= c <= '\u05ea' for c in text):
                        speak("כן אדוני?")
                    else:
                        speak("Yes, sir?")
                    continue
            else:
                continue
        else:
            command = text

        if not command:
            continue

        ai_decision = analyze_command_with_ai(command)
        intent  = ai_decision.get("intent", "general_chat")
        target  = ai_decision.get("target", "")
        value   = ai_decision.get("value", 0)
        response_text = ai_decision.get("response", "")

        # Safety net for camera intent
        if intent == "open_app" and any(
            word in target.lower() for word in ["camera", "cam", "מצלמה"]
        ):
            intent = "open_camera"

        speak(response_text)

        # ── ORIGINAL: Windows app name mapping ──────────────────
        hebrew_apps = {
            "calculator": "מחשבון", "notepad": "פנקס רשימות",
            "settings": "הגדרות", "camera": "מצלמה", "photos": "תמונות",
            "clock": "שעון", "paint": "צייר", "calendar": "לוח שנה",
            "weather": "מזג אוויר", "maps": "מפות"
        }
        windows_commands = {
            "calculator": "start calc", "notepad": "start notepad",
            "settings": "start ms-settings:", "camera": "start microsoft.windows.camera:",
            "clock": "start ms-clock:", "paint": "start mspaint",
            "photos": "start ms-photos:", "calendar": "start outlookcal:",
            "weather": "start bingweather:", "maps": "start bingmaps:"
        }
        windows_kill_processes = {
            "calculator": "CalculatorApp.exe", "notepad": "notepad.exe",
            "settings": "SystemSettings.exe", "camera": "WindowsCamera.exe",
            "clock": "Time.exe", "paint": "mspaint.exe",
            "photos": "Microsoft.Photos.exe", "weather": "Microsoft.Msn.Weather.exe"
        }
        # ──────────────────────────────────────────────────────

        if intent == "open_app":
            original_target = target.strip()
            search_target = original_target.lower()
            if "google" in search_target:
                webbrowser.open("https://www.google.com")
            elif "youtube" in search_target:
                webbrowser.open("https://www.youtube.com")
            elif search_target in windows_commands:
                os.system(windows_commands[search_target])
            else:
                try:
                    open_app(original_target, match_closest=True)
                except Exception as e:
                    print(f"Could not open {original_target}: {e}")

        elif intent == "close_app":
            original_target = target.strip()
            search_target = original_target.lower()
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            if original_target:
                speak("סוגר את התוכנה, אדוני." if is_hebrew else f"Closing {original_target}, sir.")
                if search_target in windows_kill_processes:
                    os.system(f"taskkill /F /IM {windows_kill_processes[search_target]} /T")
                else:
                    try:
                        close_app(original_target, match_closest=True, output=False)
                    except Exception as e:
                        print(f"Error closing app: {e}")
                        speak("מצטער אדוני, לא הצלחתי לסגור את התוכנה." if is_hebrew else "Sorry sir, couldn't close the app.")

        elif intent == "send_whatsapp":
            contact_name = target
            message_content = value
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            target_id = None
            is_group = False
            for name, uid in CONTACTS.items():
                if name in contact_name:
                    target_id = uid
                    is_group = not uid.startswith('+')
                    break
            if target_id:
                speak(f"פותח וואטסאפ ושולח הודעה ל{contact_name}." if is_hebrew else f"Sending message to {contact_name}.")
                def send_wa_task():
                    try:
                        safe_msg = urllib.parse.quote(message_content)
                        if not is_group:
                            clean_phone = target_id.replace("+", "")
                            webbrowser.open(f"whatsapp://send?phone={clean_phone}&text={safe_msg}")
                            time.sleep(5)
                            pyautogui.press('enter')
                        else:
                            pywhatkit.sendwhatmsg_to_group_instantly(target_id, message_content, wait_time=15, tab_close=True, close_time=4)
                            time.sleep(2)
                            pyautogui.press('enter')
                        speak("ההודעה נשלחה בהצלחה." if is_hebrew else "Message sent successfully.")
                    except Exception as e:
                        speak("סליחה אדוני, הייתה בעיה בשליחת ההודעה." if is_hebrew else "Sorry sir, there was a problem.")
                        print(f"WhatsApp Error: {e}")
                threading.Thread(target=send_wa_task, daemon=True).start()
            else:
                speak(f"לא מצאתי את {contact_name} באנשי הקשר." if is_hebrew else f"I couldn't find {contact_name} in contacts.")

        elif intent == "remember_fact":
            save_to_memory(value)
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            speak("שמרתי את זה בזיכרון, אדוני." if is_hebrew else "Committed to memory, sir.")

        elif intent == "download_media":
            media_type = str(value).lower()
            search_query = target
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            speak(f"מחפש ומוריד {media_type}, אדוני." if is_hebrew else f"Downloading {media_type} for {search_query}, sir.")
            def download_media_task():
                downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
                try:
                    if "video" in media_type:
                        ydl_opts = {
                            'outtmpl': os.path.join(downloads_path, f'{search_query}.%(ext)s'),
                            'format': 'best[ext=mp4]/best', 'quiet': True, 'noplaylist': True,
                            'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
                        }
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([f"ytsearch1:{search_query}"])
                        speak("הסרטון הורד בהצלחה." if is_hebrew else "Video downloaded.")
                    elif "image" in media_type:
                        results = DDGS().images(search_query, max_results=1)
                        if results:
                            img_data = requests.get(results[0]['image'], timeout=10).content
                            safe_name = "".join([c for c in search_query if c.isalnum() or c == ' ']).rstrip()
                            with open(os.path.join(downloads_path, f"{safe_name or 'image'}.jpg"), 'wb') as f:
                                f.write(img_data)
                            speak("התמונה הורדה בהצלחה." if is_hebrew else "Image downloaded.")
                except Exception as e:
                    print(f"Download Error: {e}")
                    speak("אירעה שגיאה במהלך ההורדה." if is_hebrew else "Download error.")
            threading.Thread(target=download_media_task, daemon=True).start()

        elif intent == "press_key":
            pyautogui.press(target.lower())

        elif intent == "identify_and_play":
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            speak("אני מקשיב למילים, שיר לי משפט או שניים אדוני." if is_hebrew else "Listening for lyrics. Sing a line or two, sir.")
            lyrics = find_song_by_lyrics()
            if lyrics:
                speak("מנגן את השיר עכשיו אדוני." if is_hebrew else "Playing it now, sir.")
                pywhatkit.playonyt(f"{lyrics} song")
            else:
                speak("מצטער אדוני, לא הצלחתי להבין את המילים." if is_hebrew else "Sorry sir, I couldn't catch the lyrics.")

        elif intent == "scroll":
            amount = 800 if target.lower() == "up" else -800
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            speak("גולל עבורך, אדוני." if is_hebrew else "Scrolling, sir.")
            pyautogui.scroll(amount)

        elif intent == "media_control":
            action = target.lower()
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            if action == 'playpause':
                speak("עוצר או מנגן." if is_hebrew else "Toggling media.")
                keyboard.send('play/pause media')
            elif action == 'nexttrack':
                speak("מעביר לשיר הבא." if is_hebrew else "Next track.")
                keyboard.send('next track')
            elif action == 'prevtrack':
                speak("חוזר לשיר הקודם." if is_hebrew else "Previous track.")
                keyboard.send('previous track')

        elif intent == "play_spotify":
            action = target.lower()
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            spotify_playlist_uri = "https://open.spotify.com/playlist/2DsODxpGSBqj4rtQH5gb0E?si=c49be2ff923e45a"
            if action == "shuffle" or "אקראי" in command:
                speak("מפעיל פלייליסט במצב אקראי, אדוני." if is_hebrew else "Playing on shuffle, sir.")
                os.startfile(spotify_playlist_uri)
                time.sleep(5)
                pyautogui.hotkey('ctrl', 's')
                time.sleep(0.5)
                pyautogui.press('space')
            elif action == "playlist" or action == "":
                speak("פותח פלייליסט, אדוני." if is_hebrew else "Opening your playlist, sir.")
                os.startfile(spotify_playlist_uri)
                time.sleep(5)
                pyautogui.press('space')
            else:
                speak(f"מחפש {target} בספוטיפיי." if is_hebrew else f"Playing {target} on Spotify.")
                os.startfile(f"spotify:search:{urllib.parse.quote(target)}")
                time.sleep(5)
                for _ in range(5):
                    pyautogui.press('tab')
                    time.sleep(0.2)
                pyautogui.press('enter')

        elif intent == "system_status":
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            if is_hebrew:
                speak(f"המערכת יציבה אדוני. המעבד ב-{cpu} אחוזים, הראם ב-{ram} אחוזים.")
            else:
                speak(f"System stable, sir. CPU at {cpu}%, RAM at {ram}%.")

        elif intent == "fix_language":
            success = fix_language_gibberish()
            if not success:
                speak("לא מצאתי טקסט לתיקון" if "תיקון" in command else "No text found to fix.")

        elif intent == "play_youtube":
            pywhatkit.playonyt(target)

        elif intent == "search_google":
            pywhatkit.search(target)

        elif intent == "get_weather_global":
            city = target if target else "london"
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            temp = get_global_weather(city)
            if temp == "ERROR":
                speak("יש בעיה בחיבור לשרת מזג האוויר." if is_hebrew else "Weather server connection error.")
            elif temp is None:
                speak(f"לא מצאתי עיר בשם {city}." if is_hebrew else f"Couldn't find city {city}.")
            else:
                speak(f"הטמפרטורה ב{city} היא {temp} מעלות." if is_hebrew else f"Temperature in {city} is {temp} degrees Celsius.")

        elif intent == "take_screenshot":
            take_temp_screenshot()
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            speak("צילמתי את המסך, אדוני. לשמור את התמונה או להעתיק אותה ללוח?" if is_hebrew
                  else "Screenshot taken, sir. Should I save it or copy to clipboard?")

        elif intent == "handle_screenshot":
            location_target = target if target else "clipboard"
            handle_existing_screenshot(location_target)
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            if location_target == "clipboard":
                speak("התמונה הועתקה ללוח." if is_hebrew else "Image copied to clipboard.")
            else:
                speak(f"התמונה נשמרה ב{location_target}." if is_hebrew else f"Image saved to {location_target}.")

        elif intent == "type_text":
            global jarvis_state
            speak("אני מאזין. כל מה שתגיד יוקלד. כשתסיים, תגיד 'עצור'.")
            try:
                while True:
                    jarvis_state = "listening"
                    text_to_type = listen()
                    if text_to_type:
                        jarvis_state = "processing"
                        if any(word in text_to_type for word in ["עצור", "תפסיק", "מספיק", "stop", "סיימתי"]):
                            speak("סיימתי להקליד, אדוני.")
                            jarvis_state = "standby"
                            break
                        keyboard.write(text_to_type)
                        keyboard.send("space")
                        time.sleep(0.2)
            except Exception as e:
                print(f"Type error: {e}")
                jarvis_state = "standby"

        elif intent == "open_website":
            site = target
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            if site == "LAST_SEARCH" or "הזה" in site or "אחרון" in site:
                if config.last_search_urls:
                    speak("פותח את מקור המידע עבורך, אדוני." if is_hebrew else "Opening the source, sir.")
                    webbrowser.open(config.last_search_urls[0])
                else:
                    speak("אין חיפוש קודם בזיכרון." if is_hebrew else "No previous search in memory.")
            else:
                if site:
                    speak(f"פותח את {site}." if is_hebrew else f"Opening {site}.")
                    site_clean = site.lower().replace(" ", "")
                    if not site_clean.startswith("http"):
                        site_clean = f"https://www.{site_clean}.com"
                    webbrowser.open(site_clean)

        elif intent == "set_volume":
            try:
                vol_val = int(value)
                if vol_val == -1: pyautogui.press("volumedown", presses=10)
                elif vol_val == -2: pyautogui.press("volumeup", presses=10)
                elif vol_val >= 0: set_system_volume(vol_val)
            except (ValueError, TypeError):
                pass

        elif intent == "set_timer":
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            try:
                threading.Thread(target=timer_thread, args=(int(value), is_hebrew), daemon=True).start()
            except (ValueError, TypeError):
                speak("לא הבנתי כמה זמן, אדוני." if is_hebrew else "I didn't understand the duration.")

        elif intent == "open_camera":
            root.after(0, lambda: open_panel("cam"))

        elif intent == "open_news":
            root.after(0, lambda: open_panel("news"))

        elif intent == "lock_pc":
            try:
                ctypes.windll.user32.LockWorkStation()
            except:
                pass

        elif intent == "add_todo":
            if target:
                todo_list.append(target.capitalize())
                save_todo_list(todo_list)
                todo_updated = True

        elif intent == "clear_todo":
            todo_list.clear()
            save_todo_list(todo_list)
            todo_updated = True

        elif intent == "standby":
            is_awake = False

        elif intent == "shutdown":
            speak("Shutting down, sir. Goodbye.")
            time.sleep(2)
            os._exit(0)

        elif intent == "get_time":
            now = datetime.datetime.now().strftime("%I:%M %p")
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            speak(f"השעה היא {now}" if is_hebrew else f"The time is {now}.")

        elif intent == "vision_analyze":
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            
            # Try camera first, then fall back to screen analysis
            frame_to_analyze = None
            if cap is not None and cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    frame_to_analyze = frame
            else:
                for cam_index in [0, 1]:
                    temp_cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
                    if temp_cap.isOpened():
                        time.sleep(1)
                        ret, frame = temp_cap.read()
                        temp_cap.release()
                        if ret:
                            frame_to_analyze = frame
                            break
            
            if frame_to_analyze is not None:
                _, buffer = cv2.imencode('.jpg', frame_to_analyze)
                b64_img = base64.b64encode(buffer).decode('utf-8')
                vision_response = analyze_image_with_ai(command, b64_img)
                speak(vision_response)
            else:
                # NEW: Fallback — analyze the screen if no camera
                speak("אין מצלמה זמינה. מנתח את המסך במקום, אדוני." if is_hebrew
                      else "No camera available. Analyzing your screen instead, sir.")
                screen_response = analyze_screen_with_ai(command)
                speak(screen_response)

        elif intent == "web_research":
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            language = "he" if is_hebrew else "en"
            search_query = target.strip() if target else command.strip()
            words_to_remove = ["ג'רוויס", "תחפש", "באינטרנט", "תמצא", "לי", "מידע", "על"]
            for word in words_to_remove:
                search_query = search_query.replace(word, "").strip()
            if search_query:
                speak(f"מחפש ברשת מידע על {search_query}." if is_hebrew else f"Searching for {search_query}, one moment.")
                raw_info = agentic_web_search(search_query, language)
                summary_prompt = f"""
You are J.A.R.V.I.S.
The user asked: '{command}'.
Search results: {raw_info}
Give a direct, helpful answer in {'Hebrew' if is_hebrew else 'English'}.
Be conversational. If results are incomplete, use your own knowledge.
"""
                final_answer = generate_text(summary_prompt, max_tokens=800)
                if not final_answer:
                    final_answer = "מצטער אדוני, לא הצלחתי לעבד את המידע." if is_hebrew else "Sorry sir, couldn't process the data."
                speak(final_answer)

        elif intent == "generate_doc":
            topic = target
            has_hebrew_topic = bool(re.search(r'[\u0590-\u05ea]', topic))
            is_english_explicit = any(w in command.lower() for w in ["english", "אנגלית", "in english"])
            is_english = is_english_explicit or not has_hebrew_topic
            language = "English" if is_english else "Hebrew"
            direction = "ltr" if is_english else "rtl"
            if topic:
                speak("How many pages, sir?" if is_english else "כמה עמודים תרצה שהעבודה תהיה אדוני?")
                pages_response = listen()
                num_pages = 3
                if pages_response:
                    try:
                        pages_str = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": f"Extract ONLY the integer number. Text: '{pages_response}'"}]
                        ).choices[0].message.content.strip()
                        match = re.search(r'\d+', pages_str)
                        if match:
                            num_pages = int(match.group())
                    except:
                        pass
                speak(f"Preparing a {num_pages} page document." if is_english else f"מכין עבודה של {num_pages} עמודים.")
                topic_english = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": f"Extract ONE concrete English noun related to: {topic}"}]
                ).choices[0].message.content.strip()
                num_chapters = max(2, num_pages * 2)
                chapter_example = "## Chapter 1: History" if is_english else "## פרק 1: היסטוריה"
                prompt = f"""Write a PROFESSIONAL academic research paper about: '{topic}'. Language: {language}.
Target: {num_pages} pages, {num_chapters} chapters. 3+ detailed paragraphs per chapter.
No repetition. Finish with Conclusion. No meta-text. Start directly.
Use '## ' before each chapter title (e.g., '{chapter_example}')."""
                try:
                    article_content = generate_text(prompt, max_tokens=8000)
                    if not article_content:
                        raise Exception("No content generated")
                    if generate_docx_document(topic, article_content, direction, topic_english):
                        speak("Document ready, sir." if is_english else "המסמך מוכן אדוני.")
                except Exception as e:
                    print(f"Doc generation error: {e}")
                    speak("Sorry sir, the server is busy. Please try again." if is_english
                          else "מצטער אדוני, השרת עמוס. אנא נסה שוב.")

        elif intent == "generate_ppt":
            topic = target
            has_hebrew_topic = bool(re.search(r'[\u0590-\u05ea]', topic))
            is_english = any(w in command.lower() for w in ["english", "אנגלית"]) or not has_hebrew_topic
            language = "English" if is_english else "Hebrew"
            direction = "ltr" if is_english else "rtl"
            if topic:
                speak(f"Creating presentation about {topic}." if is_english else f"מכין מצגת על {topic}.")
                web_info = agentic_web_search(topic, language="he" if has_hebrew_topic else "en")
                prompt = f"""Create a professional presentation about: '{topic}'. Language: {language}.
Source: {web_info[:4000]}
Create exactly 7 slides. Each bullet = full sentence with facts.
No intro text. START WITH '---SLIDE---'.
FORMAT:
---SLIDE---
TITLE: [Title]
- [Bullet 1]
- [Bullet 2]
- [Bullet 3]"""
                ppt_content = generate_text(prompt, max_tokens=3000)
                if ppt_content:
                    if generate_pptx_presentation(topic, ppt_content, direction):
                        speak("Presentation ready, sir." if is_english else "המצגת מוכנה אדוני.")
                    else:
                        speak("Error creating presentation." if is_english else "שגיאה ביצירת המצגת.")

        # ============================================================
        # NEW FEATURE: Reminder — "Remind me to call Mom in 2 hours"
        # ============================================================
        elif intent == "set_reminder":
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            reminder_text = target.strip() if target else command
            time_str = str(value).strip() if value and str(value) != "0" else "5 minutes"
            
            try:
                trigger_dt = parse_reminder_time(time_str)
                save_reminder(reminder_text, trigger_dt)
                time_display = trigger_dt.strftime("%H:%M, %d/%m")
                speak(f"בסדר אדוני, אזכיר לך '{reminder_text}' בשעה {time_display}." if is_hebrew
                      else f"Reminder set, sir. I'll remind you '{reminder_text}' at {time_display}.")
            except Exception as e:
                print(f"[REMINDER] Error: {e}")
                speak("לא הצלחתי לשמור את התזכורת." if is_hebrew else "Sorry sir, I couldn't save the reminder.")

        # ============================================================
        # NEW FEATURE: Code Execution — "Jarvis, calculate the 15th fibonacci number"
        # ============================================================
        elif intent == "run_code":
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            code_input = str(value).strip() if value and str(value) != "0" else target
            
            speak("מריץ את הקוד, אדוני. רגע." if is_hebrew else "Running the code, one moment sir.")
            
            def _run_code_task():
                result = execute_python_code(code_input, generate_text_fn=generate_text)
                print(f"[CODE] Result: {result}")
                speak(result)
            
            threading.Thread(target=_run_code_task, daemon=True).start()

        # ============================================================
        # NEW FEATURE: Email Reading — "Jarvis, read my emails"
        # ============================================================
        elif intent == "read_email":
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            speak("מאחזר את האימיילים שלך, אדוני." if is_hebrew else "Fetching your emails, one moment sir.")
            
            def _read_email_task():
                raw_emails = read_latest_emails(count=5)
                # Ask AI to summarize them naturally
                summary_prompt = (
                    f"You are Jarvis. Summarize these emails briefly and conversationally "
                    f"in {'Hebrew' if is_hebrew else 'English'}. Focus on who they're from and what they're about. "
                    f"Keep it under 5 sentences total.\n\nEmails:\n{raw_emails}"
                )
                summary = generate_text(summary_prompt, max_tokens=300)
                speak(summary if summary else raw_emails[:500])
            
            threading.Thread(target=_read_email_task, daemon=True).start()

        # ============================================================
        # NEW FEATURE: Email Sending — "Jarvis, send an email to boss@company.com"
        # ============================================================
        elif intent == "send_email":
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            recipient = target.strip()
            
            # Parse subject|body from value
            subject, body = "Message from Jarvis", "Hello"
            if value and "|" in str(value):
                parts = str(value).split("|", 1)
                subject = parts[0].strip()
                body = parts[1].strip()
            elif value and str(value) != "0":
                subject = str(value)[:80]
                body = str(value)
            
            speak(f"שולח אימייל ל{recipient}, אדוני." if is_hebrew else f"Sending email to {recipient}, sir.")
            
            def _send_email_task():
                result = send_email_message(recipient, subject, body)
                speak(result)
            
            threading.Thread(target=_send_email_task, daemon=True).start()

        # ============================================================
        # NEW FEATURE: Show Chat Log — "Jarvis, what did we talk about?"
        # ============================================================
        elif intent == "show_chat_log":
            is_hebrew = any('\u0590' <= c <= '\u05ea' for c in command)
            # Open the chat log panel in the GUI
            root.after(0, lambda: open_panel("chat"))
            
            # Also give a spoken summary of the last few exchanges
            recent = config.chat_log[-6:] if len(config.chat_log) >= 6 else config.chat_log
            if recent:
                if is_hebrew:
                    speak(f"פתחתי את יומן השיחה אדוני. היו לנו {len(config.chat_log)} הודעות בשיחה הזאת.")
                else:
                    speak(f"Opening the chat log, sir. We've had {len(config.chat_log)} messages in this session.")
            else:
                speak("יומן השיחה ריק עדיין." if is_hebrew else "The chat log is empty so far, sir.")

        elif intent == "general_chat":
            pass


# ============================================================
# STARTUP & MAIN
# ============================================================

if __name__ == "__main__":
    # Load persisted chat log from disk so GUI shows previous sessions
    from memory_manager import load_chat_log_from_disk
    load_chat_log_from_disk()
    
    # NEW: Setup global hotkey (Ctrl+J to wake Jarvis)
    _setup_hotkey()
    
    # Start the main brain thread
    brain_thread = threading.Thread(target=jarvis_brain, daemon=True, name="JarvisBrain")
    brain_thread.start()
    
    # NEW: Start watchdog thread (auto-restart brain on crash)
    watchdog_thread = threading.Thread(target=_watchdog_loop, daemon=True, name="Watchdog")
    watchdog_thread.start()
    
    # NEW: Start reminder background checker
    start_reminder_checker(speak)
    
    # NEW: Start proactive system alerts monitor
    alerts_thread = threading.Thread(target=_proactive_alerts_loop, daemon=True, name="ProactiveAlerts")
    alerts_thread.start()
    
    # Start GUI animation and update loops
    root.after(16, animate_mark_xxx)
    root.after(100, update_ui_loops)
    
    root.mainloop()