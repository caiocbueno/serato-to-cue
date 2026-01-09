import os
import json
import html

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_config(performer, last_mode):
    data = {'DefaultPerformer': performer, 'LastMode': last_mode}
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def clean_text(text):
    if not text: return ""
    return html.unescape(text).strip()

def format_timedelta(td):
    """Converts timedelta to MM:SS:00 string"""
    total_seconds = int(td.total_seconds())
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02}:{seconds:02}:00"

def get_track_artist_title(raw_name):
    """Splits 'Artist - Title' string safely"""
    raw_name = clean_text(raw_name)
    if " - " in raw_name:
        parts = raw_name.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    return "Unknown", raw_name