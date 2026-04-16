import json
import os
import datetime
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, ".env")
load_dotenv(dotenv_path=env_path)

# --- API Keys ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ============================================================
# NEW: Email Configuration
# Add these two lines to your .env file:
#   EMAIL_ADDRESS=your.gmail@gmail.com
#   EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx  (Gmail App Password)
# To generate an App Password: Google Account → Security → App Passwords
# ============================================================
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")

# ============================================================
# NEW: Porcupine Wake Word (Optional)
# Get a free key at: https://console.picovoice.ai/
# Add to .env:  PORCUPINE_KEY=your_key_here
# If not set, Jarvis falls back to Whisper-based wake word detection
# ============================================================
PORCUPINE_KEY = os.getenv("PORCUPINE_KEY", "")

# --- File Paths ---
MEMORY_FILE = "jarvis_memory.json"
TODO_FILE = "todo_list.txt"
EXHAUSTED_DAILY_CACHE_FILE = "exhausted_models_cache.json"
TEMP_SCREENSHOT = "temp_screenshot.png"
REMINDERS_FILE = "jarvis_reminders.json"   # NEW
CHAT_LOG_FILE = "jarvis_chat_log.json"     # NEW

# --- System State ---
jarvis_state = "sleeping"
current_subtitle = ""
last_search_urls = []
chat_history = []

# NEW: In-memory chat log (displayed in GUI panel)
# Each entry: {"role": "user"/"jarvis", "text": "...", "time": "HH:MM"}
chat_log = []

# NEW: Hotkey state — set to True by the hotkey listener to force wake
hotkey_wake_trigger = False

# --- Contacts ---
CONTACTS = json.loads(os.getenv("CONTACTS_JSON", "{}"))

# NAME
USER_NAME = os.getenv("USER_NAME", "sir")


def load_exhausted_models():
    try:
        if os.path.exists(EXHAUSTED_DAILY_CACHE_FILE):
            with open(EXHAUSTED_DAILY_CACHE_FILE, "r") as f:
                data = json.load(f)
            if data.get("date") == datetime.date.today().isoformat():
                return set(data.get("models", []))
    except:
        pass
    return set()

EXHAUSTED_DAILY_MODELS = load_exhausted_models()
