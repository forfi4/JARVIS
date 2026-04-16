import os
import sys
import re
import time
import random
import threading
import subprocess
import pygame
import speech_recognition as sr

import config
from ai_core import client

pygame.mixer.init()
speak_lock = threading.Lock()

# ============================================================
# NEW FEATURE 1: Amplitude Tracking (feeds the GUI waveform)
# ============================================================
# The GUI reads this value to draw animated waveform bars.
# Range: 0.0 (silent) → 1.0 (loud)
_current_amplitude = 0.0
_amp_lock = threading.Lock()

def get_current_amplitude():
    """Called by gui.py to draw the listening waveform"""
    with _amp_lock:
        return _current_amplitude

def _set_amplitude(value):
    with _amp_lock:
        global _current_amplitude
        _current_amplitude = max(0.0, min(1.0, value))

def _compute_amplitude_from_audio(audio):
    """Compute amplitude (0-1) from a SpeechRecognition AudioData object"""
    try:
        raw = audio.get_raw_data()
        if not raw or len(raw) < 2:
            return 0.0
        # Sample every 4th 16-bit sample for speed
        samples = [
            abs(int.from_bytes(raw[i:i+2], 'little', signed=True))
            for i in range(0, min(len(raw) - 1, 4000), 4)
        ]
        if samples:
            avg = sum(samples) / len(samples)
            return min(1.0, (avg / 32768.0) * 4.0)   # amplify × 4 for visibility
    except:
        pass
    return 0.0


# ============================================================
# NEW FEATURE 2: Wake Word Detection via Porcupine (optional)
# If PORCUPINE_KEY is set in .env, Jarvis uses always-on offline
# wake word detection for "Jarvis" instead of continuous Whisper calls.
# Install: pip install pvporcupine
# Free key: https://console.picovoice.ai/
# ============================================================

_porcupine_available = False
_porcupine = None

def _init_porcupine():
    global _porcupine_available, _porcupine
    if not config.PORCUPINE_KEY:
        return False
    try:
        import pvporcupine
        _porcupine = pvporcupine.create(
            access_key=config.PORCUPINE_KEY,
            keywords=["jarvis"]       # "jarvis" is a built-in free keyword!
        )
        _porcupine_available = True
        print("[WAKE WORD] Porcupine initialized — always-on 'Jarvis' detection active.")
        return True
    except ImportError:
        print("[WAKE WORD] pvporcupine not installed. Run: pip install pvporcupine")
    except Exception as e:
        print(f"[WAKE WORD] Porcupine init failed: {e}")
    return False

def _porcupine_listen_for_wake():
    """
    Blocks until the wake word 'Jarvis' is detected offline.
    Returns True when heard.
    Much more efficient than running Whisper every 3 seconds.
    """
    if not _porcupine_available or _porcupine is None:
        return False
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=_porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=_porcupine.frame_length
        )
        print("[WAKE WORD] Listening for 'Jarvis'...")
        while True:
            pcm = stream.read(_porcupine.frame_length, exception_on_overflow=False)
            import struct
            pcm_unpacked = struct.unpack_from("h" * _porcupine.frame_length, pcm)
            result = _porcupine.process(pcm_unpacked)
            if result >= 0:
                print("[WAKE WORD] 'Jarvis' detected!")
                stream.stop_stream()
                stream.close()
                pa.terminate()
                return True
    except Exception as e:
        print(f"[WAKE WORD] Porcupine listen error: {e}")
        return False


# ============================================================
# ORIGINAL + IMPROVED: Subtitle update
# ============================================================

def update_subtitle(text, show=True):
    config.current_subtitle = text if show else ""


# ============================================================
# NEW FEATURE 3: SSML Emotion in Voice
# edge-tts supports --rate and --pitch flags for emotional delivery
# ============================================================

def _get_ssml_args(text, is_hebrew):
    """
    Determine rate/pitch modifiers based on text content.
    Returns a list of extra args for edge-tts subprocess call.
    """
    if is_hebrew:
        return []  # Hebrew voice has limited prosody support
    
    text_lower = text.lower()
    
    # Excited / very positive
    if any(w in text_lower for w in ["excellent", "perfect", "outstanding", "amazing", "right away"]):
        return ["--rate", "+15%", "--pitch", "+5Hz"]
    
    # Warning / serious
    if any(w in text_lower for w in ["warning", "careful", "danger", "critical", "alert"]):
        return ["--rate", "-10%", "--pitch", "-8Hz"]
    
    # Question
    if text.strip().endswith("?"):
        return ["--pitch", "+3Hz"]
    
    # Casual / light
    if any(w in text_lower for w in ["certainly", "of course", "absolutely", "gladly"]):
        return ["--rate", "+8%"]
    
    return []


# ============================================================
# ORIGINAL + IMPROVED: listen() — adds amplitude tracking
# ============================================================

def listen(is_awake=False):
    """
    Listen and transcribe with Groq Whisper.
    Also updates amplitude for the GUI waveform.
    """
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 1.5
    
    with sr.Microphone() as source:
        config.jarvis_state = "listening" if is_awake else "sleeping"
        _set_amplitude(0.0)
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        try:
            audio = recognizer.listen(
                source,
                timeout=5 if is_awake else 3,
                phrase_time_limit=15
            )
            
            # NEW: Measure amplitude for waveform display
            amp = _compute_amplitude_from_audio(audio)
            _set_amplitude(amp)
            
            config.jarvis_state = "processing"
            
            # Transcribe with Groq Whisper
            temp_file = f"temp_audio_{random.randint(100, 999)}.wav"
            with open(temp_file, "wb") as f:
                f.write(audio.get_wav_data())
            
            with open(temp_file, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(temp_file, file.read()),
                    model="whisper-large-v3"
                )
            
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            _set_amplitude(0.0)  # Reset after transcription
            return transcription.text.lower()
            
        except Exception as e:
            print(f"[LISTEN] Error: {e}")
            _set_amplitude(0.0)
            return ""


# ============================================================
# ORIGINAL + IMPROVED: speak() — adds SSML emotion modifiers
# ============================================================

def speak(text):
    """
    Speak text using edge-tts.
    NEW: Applies rate/pitch emotion modifiers based on content.
    """
    if not text:
        return
    
    with speak_lock:
        text = text.strip()
        if not re.search(r'[a-zA-Z\u0590-\u05ea0-9]', text):
            return
        
        previous_state = config.jarvis_state
        config.jarvis_state = "speaking"
        
        chunks = [c.strip() for c in re.split(r'\n|(?<=[.!?])\s+', text) if c.strip()]
        
        for chunk in chunks:
            if not re.search(r'[a-zA-Z\u0590-\u05ea0-9]', chunk):
                continue
            
            update_subtitle(chunk, show=True)
            filename = f"voice_{random.randint(10000, 99999)}.mp3"
            
            try:
                contains_hebrew = bool(re.search(r'[\u0590-\u05ea]', chunk))
                voice = "he-IL-AvriNeural" if contains_hebrew else "en-GB-ThomasNeural"
                
                # NEW: Get SSML emotion args
                extra_args = _get_ssml_args(chunk, contains_hebrew)
                
                cmd = [
                    sys.executable, "-m", "edge_tts",
                    "--voice", voice,
                    "--text", chunk,
                    "--write-media", filename
                ] + extra_args
                
                subprocess.run(cmd, check=True, timeout=15)
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                    
            except Exception as e:
                print(f"[SPEAK] Error: {e}")
            finally:
                try:
                    pygame.mixer.music.unload()
                    if os.path.exists(filename):
                        time.sleep(0.1)
                        os.remove(filename)
                except:
                    pass
        
        config.jarvis_state = previous_state
        update_subtitle("", show=False)


# ============================================================
# NEW: Initialize Porcupine at module load (non-blocking)
# ============================================================
threading.Thread(target=_init_porcupine, daemon=True).start()
