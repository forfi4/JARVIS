import json
import os
import datetime
import config

# ============================================================
# ORIGINAL: Core Memory Functions
# ============================================================

def load_memory():
    """Load Jarvis memories from file"""
    if os.path.exists(config.MEMORY_FILE):
        try:
            with open(config.MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_to_memory(fact):
    """Save a new fact to Jarvis memory"""
    memories = load_memory()
    if fact not in memories:
        memories.append(fact)
        with open(config.MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(memories, f, ensure_ascii=False, indent=4)

def save_todo_list(todo_list):
    """Save the todo list to file"""
    with open(config.TODO_FILE, "w", encoding="utf-8") as f:
        for task in todo_list:
            f.write(task + "\n")

def save_exhausted_models(exhausted_set):
    """Save exhausted models for today"""
    try:
        with open(config.EXHAUSTED_DAILY_CACHE_FILE, "w") as f:
            json.dump({
                "date": datetime.date.today().isoformat(),
                "models": list(exhausted_set)
            }, f)
    except:
        pass


# ============================================================
# NEW FEATURE 1: Reminders System
# ============================================================

def load_reminders():
    """Load all saved reminders from disk"""
    if os.path.exists(config.REMINDERS_FILE):
        try:
            with open(config.REMINDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_reminder(text, trigger_time):
    """
    Save a new reminder to disk.
    text: what to remind
    trigger_time: datetime object of when to fire
    """
    reminders = load_reminders()
    reminders.append({
        "text": text,
        "time": trigger_time.isoformat(),
        "fired": False
    })
    with open(config.REMINDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(reminders, f, ensure_ascii=False, indent=4)
    print(f"[REMINDER] Saved: '{text}' at {trigger_time.strftime('%H:%M %d/%m/%Y')}")

def get_due_reminders():
    """
    Check for reminders that are due right now.
    Returns list of reminder texts that fired.
    Marks them as fired in the file.
    """
    reminders = load_reminders()
    now = datetime.datetime.now()
    due_texts = []
    
    for r in reminders:
        try:
            t = datetime.datetime.fromisoformat(r["time"])
            if not r["fired"] and now >= t:
                r["fired"] = True
                due_texts.append(r["text"])
        except:
            pass
    
    # Write back with fired states updated
    with open(config.REMINDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(reminders, f, ensure_ascii=False, indent=4)
    
    return due_texts

def list_active_reminders():
    """Return all reminders that have not fired yet"""
    reminders = load_reminders()
    return [r for r in reminders if not r.get("fired", False)]


# ============================================================
# NEW FEATURE 2: Chat Log (persistent conversation history for GUI)
# ============================================================

def append_to_chat_log(role, text):
    """
    Add a message to the in-memory chat log AND persist it to disk.
    role: "user" or "jarvis"
    text: message content
    """
    entry = {
        "role": role,
        "text": text,
        "time": datetime.datetime.now().strftime("%H:%M")
    }
    # Update in-memory list
    config.chat_log.append(entry)
    if len(config.chat_log) > 100:
        config.chat_log = config.chat_log[-100:]
    
    # Persist to file (keep last 200)
    try:
        existing = []
        if os.path.exists(config.CHAT_LOG_FILE):
            with open(config.CHAT_LOG_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        existing.append(entry)
        if len(existing) > 200:
            existing = existing[-200:]
        with open(config.CHAT_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[CHATLOG] Save error: {e}")

def load_chat_log_from_disk():
    """
    Called once at startup to restore the chat log into config.chat_log
    so the GUI panel shows previous conversations.
    """
    if os.path.exists(config.CHAT_LOG_FILE):
        try:
            with open(config.CHAT_LOG_FILE, 'r', encoding='utf-8') as f:
                config.chat_log = json.load(f)[-100:]
            print(f"[CHATLOG] Loaded {len(config.chat_log)} entries from disk.")
        except:
            config.chat_log = []
    else:
        config.chat_log = []


# ============================================================
# NEW FEATURE 3: Automatic Conversation Memory Summarization
# ============================================================

def summarize_chat_history_if_needed(chat_history, generate_text_fn):
    """
    When chat_history grows past 20 messages, summarize the oldest 15
    into a compact memory fact, then trim the list.
    This prevents token overflow and keeps Jarvis smart long-term.
    
    Args:
        chat_history: list of {"role":..., "content":...} dicts
        generate_text_fn: the generate_text function from ai_core
    Returns:
        The (possibly trimmed) chat_history list
    """
    if len(chat_history) < 20:
        return chat_history
    
    oldest = chat_history[:15]
    rest = chat_history[15:]
    
    convo_text = "\n".join([
        f"{m['role'].upper()}: {m['content']}" for m in oldest
    ])
    
    summary_prompt = (
        "Summarize the following conversation into 3-5 bullet points of key facts. "
        "Focus on: things the user said about themselves, decisions made, preferences mentioned. "
        "Be very concise. Each bullet point = one clear fact.\n\n"
        f"Conversation:\n{convo_text}\n\n"
        "Return ONLY the bullet points. No preamble. No explanations."
    )
    
    try:
        summary = generate_text_fn(summary_prompt, max_tokens=300, temperature=0.3)
        if summary and len(summary) > 20:
            fact = f"[Auto-Summary {datetime.date.today()}]: {summary.strip()}"
            save_to_memory(fact)
            print(f"[MEMORY] Summarized {len(oldest)} messages → saved to long-term memory.")
    except Exception as e:
        print(f"[MEMORY] Summarization error: {e}")
    
    return rest