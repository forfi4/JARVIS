import os
import time
import shutil
import platform
import socket
import datetime
import subprocess
import webbrowser
import psutil
import pyautogui
import pyperclip


# הגדרת נתיב זמני לצילום מסך (משתמש בתיקיית Temp של המערכת)
TEMP_SCREENSHOT = os.path.join(os.environ.get('TEMP', '.'), 'jarvis_temp_snap.png')

# --- פונקציות צילום מסך וניהול קבצים ---

def take_temp_screenshot():
    """שומר צילום מסך לקובץ זמני"""
    try:
        filepath = os.path.abspath(TEMP_SCREENSHOT)
        pyautogui.screenshot(filepath)
        return True
    except Exception as e:
        print(f"Screenshot Error: {e}")
        return False

def handle_existing_screenshot(action):
    """בודק מה לעשות עם הצילום הזמני: שולחן עבודה, הורדות או לוח עריכה"""
    if not os.path.exists(TEMP_SCREENSHOT):
        return "No screenshot found to process."
        
    timestamp = int(time.time())
    
    if action == "desktop":
        dest = os.path.join(os.environ['USERPROFILE'], 'Desktop', f"screenshot_{timestamp}.png")
        shutil.move(TEMP_SCREENSHOT, dest)
        return f"Saved to Desktop, sir."
        
    elif action == "downloads":
        dest = os.path.join(os.environ['USERPROFILE'], 'Downloads', f"screenshot_{timestamp}.png")
        shutil.move(TEMP_SCREENSHOT, dest)
        return f"Saved to Downloads, sir."
        
    else:
        # העתקה ללוח (Clipboard) באמצעות PowerShell ואז מחיקה
        filepath = os.path.abspath(TEMP_SCREENSHOT)
        # פקודת PowerShell להזנת תמונה ל-Clipboard
        cmd = f"powershell -command \"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetImage([System.Drawing.Image]::FromFile('{filepath}'))\""
        subprocess.run(cmd, shell=True)
        
        # שחרור הקובץ ומחיקתו
        if os.path.exists(TEMP_SCREENSHOT):
            os.remove(TEMP_SCREENSHOT)
        return "Screenshot copied to clipboard."

# --- שליטה בחומרה וממשק ---

def set_system_volume(level):
    """שינוי ווליום המערכת (0-100)"""
    try:
        level = max(0, min(100, level))
        # מאפסים את הווליום ואז מעלים לרמה הרצויה
        pyautogui.press("volumedown", presses=50) 
        pyautogui.press("volumeup", presses=int(level / 2))
    except: 
        pass

def open_website(url):
    """פתיחת אתר אינטרנט"""
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)

def type_text_via_clipboard(text):
    """הקלדת טקסט דרך הלוח כדי לתמוך בעברית ותווים מיוחדים"""
    old_clipboard = pyperclip.paste()
    pyperclip.copy(text)
    time.sleep(0.1)
    
    # שימוש ב-Shift+Insert נחשב יציב יותר בקיצורי דרך מסוימים
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.1)
    
    pyperclip.copy(old_clipboard)

# --- ניטור ותחזוקת מערכת (שילוב מהגרסה הקודמת) ---

def get_system_stats():
    """נתוני מעבד וזיכרון עבור ה-GUI"""
    return psutil.cpu_percent(), psutil.virtual_memory().percent

def clean_junk_files():
    """ניקוי תיקיות Temp של ווינדוס"""
    temp_paths = [os.environ.get('TEMP'), r'C:\Windows\Temp']
    count = 0
    for path in temp_paths:
        if not path or not os.path.exists(path): continue
        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    count += 1
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    count += 1
            except: continue
    return f"I have cleared {count} temporary files, sir."

def get_ip_address():
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "127.0.0.1"