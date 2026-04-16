# 🤖 JARVIS: The Intent-Driven Personal Assistant

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Status](https://img.shields.io/badge/Status-Development-green?style=for-the-badge)
![Dev](https://img.shields.io/badge/Developer-Liam-blue?style=for-the-badge)

Welcome to **JARVIS**, a sophisticated personal assistant designed to bridge the gap between human language and OS-level automation. Built with a focus on intent recognition and seamless system integration.

---

## 🚀 Overview
JARVIS isn't just a chatbot; it’s a command center. By utilizing a custom intent-parsing engine, this project can handle everything from system architecture control to real-time web research and media management.

### 🧠 Core Intelligence
The system operates on a strict **Intent-Action** framework. Every request is classified into a specific intent, ensuring high accuracy and preventing "hallucinated" actions.

---

## 🛠️ Key Capabilities

### 📱 Communication & Social
* **send_whatsapp / send_email / read_email**: Full messaging integration.
* **general_chat**: Natural conversation mode.
* **show_chat_log**: Review previous interactions.

### 💻 System Control & Navigation
* **open_app / close_app**: Launch or terminate desktop applications.
* **lock_pc / shutdown / standby**: Power and security management.
* **set_volume / system_status**: Hardware monitoring and control.
* **take_screenshot / handle_screenshot**: Visual capture and processing.
* **press_key / scroll / type_text**: Direct HID (Human Interface Device) simulation.

### ✍️ Productivity & Documents
* **generate_doc / generate_ppt**: Automated document and presentation creation.
* **add_todo / clear_todo**: Task management.
* **set_timer / set_reminder / get_time**: Time-based automation.
* **fix_language**: Advanced grammar and syntax correction.

### 🌐 Web & Research
* **web_research / search_google**: Deep-dive information gathering.
* **get_weather_global**: Real-time meteorological data.
* **play_youtube / play_spotify**: Instant media streaming.
* **open_website**: Browser automation.

### 👁️ Vision & Advanced Logic
* **vision_analyze**: Image recognition and context understanding.
* **run_code**: Execute dynamic scripts on the fly.
* **remember_fact**: Long-term memory storage.

---

## 🔧 Technical Implementation

The engine uses a rigorous classification system. Every user input is mapped to a specific intent string to ensure the system remains stable and predictable.

> **Note:** The intent must be exactly one of the pre-defined keys in the system's logic to trigger the corresponding automation script.

```json
{
  "intent": "identify_and_play",
  "confidence_threshold": 0.95,
  "status": "ready"
}
📈 Future Roadmap
[ ] Integration with more IoT devices.

[ ] Advanced voice-to-intent latency reduction.

[ ] Multi-language support (Hebrew/English).

👤 About the Author
I'm a 14-year-old developer from Israel 🇮🇱 with a passion for AI, automation, and building tools that make life feel a little more like a Sci-Fi movie.