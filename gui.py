import customtkinter as ctk
import tkinter as tk
import cv2
import psutil
import math
import random
import time
import datetime
import urllib.request
import xml.etree.ElementTree as ET
import threading
import textwrap
import os
from PIL import Image

import config
import skills
import audio_engine
import ai_core

# ============================================================
# ORIGINAL: Globals
# ============================================================
todo_list = []
todo_updated = True
_chat_log_update_needed = True   # NEW: flag to refresh chat log panel

def load_todo_list():
    global todo_list
    if os.path.exists("todo.txt"):
        with open("todo.txt", "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines()]
    return []

def save_todo_list():
    with open("todo.txt", "w", encoding="utf-8") as f:
        for task in todo_list:
            f.write(task + "\n")

todo_list = load_todo_list()

def update_subtitle(text, show=True):
    config.current_subtitle = text if show else ""

def jarvis_brain():
    """Placeholder — real brain runs in main.py"""
    while True:
        try:
            time.sleep(2)
        except Exception as e:
            print(f"Brain Error: {e}")
            time.sleep(1)

# ============================================================
# ORIGINAL: Root Window & Left Panel
# ============================================================

root = ctk.CTk()
root.title("J.A.R.V.I.S. MARK XXX")
root.geometry("950x600")
root.resizable(False, False)
root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(0, weight=1)

left_panel = ctk.CTkFrame(root, width=250, corner_radius=0, fg_color="#010c10")
left_panel.grid(row=0, column=0, sticky="nsew")
left_panel.grid_propagate(False)

ctk.CTkLabel(left_panel, text="FEATURES", font=("Courier New", 20, "bold"), text_color="#00d4ff").pack(pady=(20, 10))
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

current_open = None
cap = None

def open_panel(panel_name):
    global current_open, cap
    todo_scroll_frame.pack_forget()
    sys_frame.pack_forget()
    news_frame.pack_forget()
    cam_frame.pack_forget()
    chat_log_frame.pack_forget()   # NEW

    if panel_name != "cam" and cap is not None:
        cap.release()
        cap = None

    if current_open == panel_name:
        current_open = None
    else:
        current_open = panel_name
        if panel_name == "todo":
            todo_scroll_frame.pack(padx=10, pady=5, fill="both", expand=True)
            global todo_updated
            todo_updated = True
        elif panel_name == "sys":
            sys_frame.pack(padx=10, pady=5, fill="both", expand=True)
        elif panel_name == "news":
            news_frame.pack(padx=10, pady=5, fill="both", expand=True)
            load_news()
        elif panel_name == "cam":
            cam_frame.pack(padx=10, pady=5, fill="both", expand=True)
            if cap is None:
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        elif panel_name == "chat":   # NEW
            chat_log_frame.pack(padx=10, pady=5, fill="both", expand=True)
            global _chat_log_update_needed
            _chat_log_update_needed = True

# --- Todo ---
todo_btn = ctk.CTkButton(left_panel, text="📋 My To-Do List", command=lambda: open_panel("todo"),
    font=("Courier New", 13, "bold"), fg_color="#003344", hover_color="#007a99", anchor="w")
todo_btn.pack(pady=5, padx=15, fill="x")
todo_scroll_frame = ctk.CTkScrollableFrame(left_panel, fg_color="#001520", corner_radius=5)

# --- System Monitor ---
sys_btn = ctk.CTkButton(left_panel, text="📊 System Monitor", command=lambda: open_panel("sys"),
    font=("Courier New", 13, "bold"), fg_color="#003344", hover_color="#007a99", anchor="w")
sys_btn.pack(pady=5, padx=15, fill="x")
sys_frame = ctk.CTkFrame(left_panel, fg_color="#001520", corner_radius=5)
cpu_label = ctk.CTkLabel(sys_frame, text="CPU Usage: 0%", text_color="#8ffcff", font=("Courier New", 12))
cpu_label.pack(pady=(10, 0))
cpu_bar = ctk.CTkProgressBar(sys_frame, width=200, progress_color="#00d4ff")
cpu_bar.pack(pady=5)
cpu_bar.set(0)
ram_label = ctk.CTkLabel(sys_frame, text="RAM Usage: 0%", text_color="#8ffcff", font=("Courier New", 12))
ram_label.pack(pady=(10, 0))
ram_bar = ctk.CTkProgressBar(sys_frame, width=200, progress_color="#ff6600")
ram_bar.pack(pady=5)
ram_bar.set(0)

# --- News ---
news_btn = ctk.CTkButton(left_panel, text="📰 Daily News", command=lambda: open_panel("news"),
    font=("Courier New", 13, "bold"), fg_color="#003344", hover_color="#007a99", anchor="w")
news_btn.pack(pady=5, padx=15, fill="x")
news_frame = ctk.CTkScrollableFrame(left_panel, fg_color="#001520", corner_radius=5)
news_loaded = False

def load_news():
    global news_loaded
    if not news_loaded:
        for widget in news_frame.winfo_children():
            widget.destroy()
        try:
            req = urllib.request.Request("https://feeds.bbci.co.uk/news/rss.xml", headers={'User-Agent': 'Mozilla/5.0'})
            xml_data = urllib.request.urlopen(req, timeout=5).read()
            root_xml = ET.fromstring(xml_data)
            for item in root_xml.findall('.//item')[:5]:
                title = item.find('title').text
                ctk.CTkLabel(news_frame, text="• " + title, text_color="#8ffcff",
                    font=("Courier New", 11), wraplength=190, justify="left").pack(pady=5, anchor="w")
            news_loaded = True
        except:
            ctk.CTkLabel(news_frame, text="Failed to load news.", text_color="red").pack()

# --- Camera ---
cam_btn = ctk.CTkButton(left_panel, text="📷 Security Camera", command=lambda: open_panel("cam"),
    font=("Courier New", 13, "bold"), fg_color="#003344", hover_color="#007a99", anchor="w")
cam_btn.pack(pady=5, padx=15, fill="x")
cam_frame = ctk.CTkFrame(left_panel, fg_color="#001520", corner_radius=5)
cam_label = ctk.CTkLabel(cam_frame, text="Loading Feed...")
cam_label.pack(pady=10)

# ============================================================
# NEW FEATURE: Chat Log Panel
# Shows the live conversation history between user and Jarvis.
# Updates in real time as you speak.
# ============================================================

chat_log_btn = ctk.CTkButton(
    left_panel, text="💬 Chat Log",
    command=lambda: open_panel("chat"),
    font=("Courier New", 13, "bold"),
    fg_color="#003344", hover_color="#007a99", anchor="w"
)
chat_log_btn.pack(pady=5, padx=15, fill="x")
chat_log_frame = ctk.CTkScrollableFrame(left_panel, fg_color="#001520", corner_radius=5)

_last_chat_log_len = 0  # Track how many entries we've already rendered

def _refresh_chat_log_panel():
    """Rebuild the chat log panel with all entries from config.chat_log"""
    global _last_chat_log_len
    
    current_len = len(config.chat_log)
    if current_len == _last_chat_log_len:
        return  # Nothing new
    
    # Only add NEW entries (don't rebuild entire panel every frame — too slow)
    new_entries = config.chat_log[_last_chat_log_len:]
    
    for entry in new_entries:
        role = entry.get("role", "user")
        text = entry.get("text", "")
        t = entry.get("time", "")
        
        if role == "user":
            color = "#00d4ff"
            prefix = f"[{t}] You: "
        else:
            color = "#ff8800"
            prefix = f"[{t}] Jarvis: "
        
        # Wrap long text
        display_text = textwrap.fill(f"{prefix}{text}", width=30)
        
        lbl = ctk.CTkLabel(
            chat_log_frame,
            text=display_text,
            text_color=color,
            font=("Courier New", 10),
            wraplength=200,
            justify="left",
            anchor="w"
        )
        lbl.pack(pady=2, padx=5, anchor="w", fill="x")
    
    _last_chat_log_len = current_len

# ============================================================
# ORIGINAL: UI Update Loop — extended with chat log refresh
# ============================================================

def update_ui_loops():
    global todo_updated, _chat_log_update_needed
    
    if current_open == "todo" and todo_updated:
        for widget in todo_scroll_frame.winfo_children():
            widget.destroy()
        if not todo_list:
            ctk.CTkLabel(todo_scroll_frame, text="List is empty.", text_color="#8ffcff",
                font=("Courier New", 12)).pack(pady=10)
        else:
            for task in todo_list:
                chk = ctk.CTkCheckBox(todo_scroll_frame, text=task, text_color="#8ffcff",
                    font=("Courier New", 12), hover_color="#00d4ff", border_color="#007a99",
                    command=lambda t=task: root.after(400, lambda: remove_task_ui(t)))
                chk.pack(pady=7, anchor="w", padx=5)
        todo_updated = False

    if current_open == "sys":
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        cpu_bar.set(cpu / 100.0)
        ram_bar.set(ram / 100.0)
        cpu_label.configure(text=f"CPU Usage: {cpu}%")
        ram_label.configure(text=f"RAM Usage: {ram}%")

    if current_open == "cam" and cap is not None:
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(210, 160))
            cam_label.configure(image=ctk_img, text="")

    # NEW: Refresh chat log panel if open
    if current_open == "chat":
        _refresh_chat_log_panel()

    root.after(100, update_ui_loops)

def remove_task_ui(task):
    global todo_updated
    if task in todo_list:
        todo_list.remove(task)
        save_todo_list()
        todo_updated = True

# ============================================================
# ORIGINAL: Canvas & Animation Setup
# ============================================================

center_frame = tk.Frame(root, bg="#000000")
center_frame.grid(row=0, column=1, sticky="nsew")

W, H = 700, 600
canvas = tk.Canvas(center_frame, width=W, height=H, bg="#000000", highlightthickness=0)
canvas.pack(fill="both", expand=True)

FACE_SZ = 380
FCX, FCY = W // 2, H // 2 + 20
tick = 0
last_t = time.time()
scale = 1.0
target_scale = 1.0
halo_a = 60.0
target_halo = 60.0
scan_angle, scan2_angle = 0.0, 180.0
rings_spin = [0.0, 120.0, 240.0]
pulse_r = [0.0, FACE_SZ * 0.26, FACE_SZ * 0.52]
status_blink = True

# NEW: Waveform bar state
_waveform_bars = [random.uniform(0.1, 0.4) for _ in range(20)]
_waveform_tick = 0

def _ac(r, g, b, a):
    f = max(0, min(1, a / 255.0))
    return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"

def animate_mark_xxx():
    global tick, last_t, scale, target_scale, halo_a, target_halo
    global scan_angle, scan2_angle, rings_spin, pulse_r, status_blink
    global _waveform_bars, _waveform_tick

    tick += 1
    _waveform_tick += 1
    now = time.time()
    speaking = (config.jarvis_state == "speaking")
    listening = (config.jarvis_state == "listening")

    if now - last_t > (0.14 if speaking else 0.55):
        if speaking:
            target_scale = random.uniform(1.05, 1.11)
            target_halo = random.uniform(138, 182)
        else:
            target_scale = random.uniform(1.001, 1.007)
            target_halo = random.uniform(50, 68)
        last_t = now

    sp = 0.35 if speaking else 0.16
    scale += (target_scale - scale) * sp
    halo_a += (target_halo - halo_a) * sp

    for i, spd in enumerate([1.2, -0.8, 1.9] if speaking else [0.5, -0.3, 0.82]):
        rings_spin[i] = (rings_spin[i] + spd) % 360

    scan_angle = (scan_angle + (2.8 if speaking else 1.2)) % 360
    scan2_angle = (scan2_angle + (-1.7 if speaking else -0.68)) % 360

    pspd = 3.8 if speaking else 1.8
    limit = FACE_SZ * 0.72
    new_p = [r + pspd for r in pulse_r if r + pspd < limit]
    if len(new_p) < 3 and random.random() < (0.06 if speaking else 0.022):
        new_p.append(0.0)
    pulse_r = new_p

    if tick % 40 == 0:
        status_blink = not status_blink

    # NEW: Update waveform bars
    if listening:
        amp = audio_engine.get_current_amplitude()
        # Each bar slowly drifts, but jumps when there's real audio
        if _waveform_tick % 3 == 0:
            for i in range(len(_waveform_bars)):
                noise = random.uniform(-0.05, 0.05)
                if amp > 0.05:
                    # Real audio: bars jump energetically
                    _waveform_bars[i] = max(0.1, min(1.0,
                        amp * random.uniform(0.5, 1.5) + noise))
                else:
                    # Silence: bars settle low
                    _waveform_bars[i] = max(0.05, min(0.25,
                        _waveform_bars[i] * 0.85 + random.uniform(0.01, 0.04)))
    else:
        # Slowly fade bars back to zero when not listening
        if _waveform_tick % 5 == 0:
            _waveform_bars = [max(0.0, b * 0.8) for b in _waveform_bars]

    draw_mark_xxx()
    root.after(16, animate_mark_xxx)


def draw_mark_xxx():
    c = canvas
    FW = FACE_SZ
    c.delete("all")

    # Background grid
    for x in range(0, W, 44):
        for y in range(0, H, 44):
            c.create_rectangle(x, y, x+1, y+1, fill="#001520", outline="")

    # Halo rings
    for r in range(int(FW * 0.54), int(FW * 0.28), -22):
        frac = 1.0 - (r - FW * 0.28) / (FW * 0.26)
        ga = max(0, min(255, int(halo_a * 0.09 * frac)))
        c.create_oval(FCX-r, FCY-r, FCX+r, FCY+r, outline=f"#00{ga:02x}ff", width=2)

    # Pulse rings
    for pr in pulse_r:
        pa = max(0, int(220 * (1.0 - pr / (FW * 0.72))))
        r = int(pr)
        c.create_oval(FCX-r, FCY-r, FCX+r, FCY+r, outline=_ac(0, 212, 255, pa), width=2)

    # Spinning arcs
    for idx, (r_frac, w_ring, arc_l, gap) in enumerate([
        (0.47, 3, 110, 75), (0.39, 2, 75, 55), (0.31, 1, 55, 38)
    ]):
        ring_r = int(FW * r_frac)
        base_a = rings_spin[idx]
        a_val = max(0, min(255, int(halo_a * (1.0 - idx * 0.18))))
        col = _ac(0, 212, 255, a_val)
        for s in range(360 // (arc_l + gap)):
            start = (base_a + s * (arc_l + gap)) % 360
            c.create_arc(FCX-ring_r, FCY-ring_r, FCX+ring_r, FCY+ring_r,
                start=start, extent=arc_l, outline=col, width=w_ring, style="arc")

    # Scanner arcs
    sr = int(FW * 0.49)
    scan_a = min(255, int(halo_a * 1.4))
    arc_ext = 70 if config.jarvis_state == "speaking" else 42
    c.create_arc(FCX-sr, FCY-sr, FCX+sr, FCY+sr,
        start=scan_angle, extent=arc_ext, outline=_ac(0, 212, 255, scan_a), width=3, style="arc")
    c.create_arc(FCX-sr, FCY-sr, FCX+sr, FCY+sr,
        start=scan2_angle, extent=arc_ext, outline=_ac(255, 100, 0, scan_a // 2), width=2, style="arc")

    # Tick marks
    t_out, t_in = int(FW * 0.495), int(FW * 0.472)
    a_mk = _ac(0, 212, 255, 155)
    for deg in range(0, 360, 10):
        rad = math.radians(deg)
        inn = t_in if deg % 30 == 0 else t_in + 5
        c.create_line(FCX + t_out * math.cos(rad), FCY - t_out * math.sin(rad),
            FCX + inn * math.cos(rad), FCY - inn * math.sin(rad), fill=a_mk, width=1)

    # Crosshair
    ch_r, gap = int(FW * 0.50), int(FW * 0.15)
    ch_a = _ac(0, 212, 255, int(halo_a * 0.55))
    for x1, y1, x2, y2 in [
        (FCX-ch_r, FCY, FCX-gap, FCY), (FCX+gap, FCY, FCX+ch_r, FCY),
        (FCX, FCY-ch_r, FCX, FCY-gap), (FCX, FCY+gap, FCX, FCY+ch_r)
    ]:
        c.create_line(x1, y1, x2, y2, fill=ch_a, width=1)

    # Corner brackets
    bc = _ac(0, 212, 255, 200)
    hl, hr, ht, hb = FCX - FW//2, FCX + FW//2, FCY - FW//2, FCY + FW//2
    for bx, by, sdx, sdy in [(hl, ht, 1, 1), (hr, ht, -1, 1), (hl, hb, 1, -1), (hr, hb, -1, -1)]:
        c.create_line(bx, by, bx + sdx * 22, by, fill=bc, width=2)
        c.create_line(bx, by, bx, by + sdy * 22, fill=bc, width=2)

    # Core orb
    orb_r = int(FW * 0.27 * scale)
    for i in range(7, 0, -1):
        r2 = int(orb_r * i / 7)
        frac = i / 7
        ga = max(0, min(255, int(halo_a * 1.1 * frac)))
        c.create_oval(FCX-r2, FCY-r2, FCX+r2, FCY+r2,
            fill=_ac(0, int(65*frac), int(120*frac), ga), outline="")

    c.create_text(FCX, FCY, text="J.A.R.V.I.S",
        fill=_ac(0, 212, 255, min(255, int(halo_a * 2))),
        font=("Arial", 14, "bold"))

    # Header bar
    HDR = 62
    c.create_rectangle(0, 0, W, HDR, fill="#00080d", outline="")
    c.create_line(0, HDR, W, HDR, fill="#007a99", width=1)
    c.create_text(W // 2, 22, text="J.A.R.V.I.S", fill="#00d4ff", font=("Courier New", 18, "bold"))
    c.create_text(W // 2, 44, text="Just A Rather Very Intelligent System", fill="#007a99", font=("Courier New", 9))
    c.create_text(16, 31, text="MARK XXX", fill="#007a99", font=("Courier New", 9), anchor="w")
    now_time = datetime.datetime.now().strftime("%H:%M:%S")
    c.create_text(W - 16, 31, text=now_time, fill="#00d4ff", font=("Courier New", 14, "bold"), anchor="e")

    # Status text
    sy = FCY + FW // 2 + 45
    if config.jarvis_state == "sleeping":     stat, sc = ("STANDBY", "#007a99")
    elif config.jarvis_state == "listening":  stat, sc = ("LISTENING...", "#00d4ff")
    elif config.jarvis_state == "processing": stat, sc = ("PROCESSING...", "#ffcc00")
    elif config.jarvis_state == "speaking":   stat, sc = ("● SPEAKING", "#ff6600")
    else:                                      stat, sc = (f"{'●' if status_blink else '○'} ONLINE", "#00d4ff")
    c.create_text(W // 2, sy, text=stat, fill=sc, font=("Arial", 11, "bold"))

    # ============================================================
    # NEW FEATURE: Animated Waveform during LISTENING state
    # Draws vertical bars that react to microphone amplitude.
    # ============================================================
    if config.jarvis_state == "listening":
        num_bars = len(_waveform_bars)
        bar_w = 6
        bar_spacing = 4
        total_w = num_bars * (bar_w + bar_spacing)
        start_x = W // 2 - total_w // 2
        base_y = sy - 35
        max_bar_h = 30

        for i, amp in enumerate(_waveform_bars):
            bx = start_x + i * (bar_w + bar_spacing)
            bar_h = max(3, int(amp * max_bar_h))
            # Colour: brighter bars = louder
            brightness = int(150 + amp * 105)
            brightness = min(255, brightness)
            bar_color = f"#00{brightness:02x}ff"
            c.create_rectangle(
                bx, base_y - bar_h,
                bx + bar_w, base_y,
                fill=bar_color, outline=""
            )

    # Subtitles
    if config.current_subtitle:
        has_hebrew = any('\u0590' <= ch <= '\u05ea' for ch in config.current_subtitle)
        if has_hebrew:
            lines = textwrap.wrap(config.current_subtitle[::-1], width=55)
            lines = [line[::-1] for line in lines]
            lines = lines[::-1]
        else:
            lines = textwrap.wrap(config.current_subtitle, width=55)

        start_y = H - 90
        box_h = len(lines) * 25 + 20
        c.create_rectangle(W//2 - 360, start_y - 15, W//2 + 360, start_y - 15 + box_h,
            fill="#000c14", outline="#003344", width=1)
        for i, line in enumerate(lines):
            c.create_text(W // 2, start_y + (i * 25), text=line,
                fill="#00d4ff", font=("Arial", 14, "bold"), justify="center")