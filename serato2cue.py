import os
import json
import re
import sys
from datetime import datetime, timedelta
import html

# --- EXTERNAL LIBRARIES ---
try:
    import requests
    from bs4 import BeautifulSoup
    import pyperclip
except ImportError:
    print("\n\033[91m[!] CRITICAL ERROR: Missing dependencies.\033[0m")
    print("Please install the required libraries by running:")
    print("\n    \033[93mpip install -r requirements.txt\033[0m\n")
    input("Press Enter to exit...")
    sys.exit()

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

# --- FORMATTING HELPERS ---
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

# --- PARSERS ---

def parse_serato_history_clipboard(raw_text):
    lines = raw_text.splitlines()
    tracks = []
    mix_date = ""
    first_start_time = None
    time_regex = re.compile(r"(\d{1,2}:\d{2}:\d{2})")
    
    # Try to find date in header
    for line in lines:
        date_match = re.search(r"(\d{2}/\d{2}/\d{4})", line)
        if date_match:
            mix_date = date_match.group(1)
            break
            
    line_buffer = ""
    
    for line in lines:
        line = line.strip()
        
        # Filters
        if not line or line.startswith("-") or "Song" in line and "Start Time" in line:
            continue
        # Session summary bug fix (ignoring lines that have both date and time)
        if re.match(r"^\d{2}/\d{2}/\d{4}.*\d{1,2}:\d{2}:\d{2}", line):
            continue

        time_match = time_regex.search(line)
        
        if time_match:
            found_time_str = time_match.group(1)
            # Remove time from line to get the song info
            text_part = line.replace(found_time_str, "").strip()
            full_track_string = f"{line_buffer} {text_part}".strip()
            line_buffer = ""
            
            # Split columns (usually separated by double spaces)
            cols = re.split(r"\s{2,}", full_track_string)
            
            if len(cols) >= 2:
                artist = cols[-1]
                title = " ".join(cols[:-1])
            else:
                title = cols[0]
                artist = "Unknown"
            
            # Protection against time-like artists
            if re.match(r"^\d{1,2}:\d{2}:\d{2}$", artist):
                artist = "Unknown"

            # Time Calculation
            try:
                dt_format = "%H:%M:%S"
                curr_dt = datetime.strptime(found_time_str, dt_format)
                
                if first_start_time is None:
                    first_start_time = curr_dt
                    rel_time = timedelta(0)
                else:
                    rel_time = curr_dt - first_start_time
                    if rel_time.total_seconds() < 0: # Midnight crossover
                         rel_time += timedelta(days=1)
                
                tracks.append({
                    'time': rel_time, # Storing as timedelta object
                    'title': clean_text(title),
                    'artist': clean_text(artist)
                })
            except ValueError:
                pass
        else:
            if not re.match(r"^\d{2}/\d{2}/\d{4}", line):
                line_buffer += " " + line

    return {'Date': mix_date, 'Tracks': tracks}

def get_serato_playlist_web(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Metadata
        title_tag = soup.find('title')
        raw_title = title_tag.text.replace(" - Serato DJ Playlists", "").strip() if title_tag else "Unknown Mix"
        performer = "Unknown DJ"
        
        # Parse Title - DJ
        if " - " in raw_title:
            parts = raw_title.split(" - ")
            performer = parts[-1].strip()
            album_title = " - ".join(parts[:-1]).strip()
        else:
            album_title = raw_title

        # Date
        mix_date = ""
        date_elem = soup.find(class_='playlist-date')
        if date_elem:
            mix_date = date_elem.text.strip()
            
        # Tracks
        tracks = []
        # Finding tracks using BeautifulSoup selectors (Robust)
        track_elements = soup.select('.playlist-track-container') # This class wraps rows often
        
        # Fallback if container structure is different, iterate direct items
        if not track_elements:
            # Try finding elements that contain the time class
            times = soup.select('.playlist-tracktime')
            for t in times:
                parent = t.find_parent('div') # Assuming div wrapper
                if parent: track_elements.append(parent)

        for row in track_elements:
            time_div = row.select_one('.playlist-tracktime')
            name_div = row.select_one('.playlist-trackname')
            
            if time_div and name_div:
                time_str = time_div.text.strip()
                full_name = name_div.text.strip()
                t_artist, t_title = get_track_artist_title(full_name)
                
                # Convert time string (MM:SS or HH:MM:SS) to timedelta
                parts = list(map(int, time_str.split(':')))
                if len(parts) == 2:
                    td = timedelta(minutes=parts[0], seconds=parts[1])
                elif len(parts) == 3:
                    td = timedelta(hours=parts[0], minutes=parts[1], seconds=parts[2])
                else:
                    td = timedelta(0)

                tracks.append({
                    'time': td,
                    'title': t_title,
                    'artist': t_artist
                })
                
        return {'Title': album_title, 'Performer': performer, 'Date': mix_date, 'Tracks': tracks}

    except Exception as e:
        print(f"Error fetching URL: {e}")
        return None

# --- CUE GENERATOR ---
def save_cue_file(data, filename_override=None):
    if not data or not data.get('Tracks'):
        print("No tracks to save.")
        return

    clean_performer = data.get('Performer', 'Unknown').replace('"', "'")
    clean_title = data.get('Title', 'Unknown').replace('"', "'")
    clean_date = data.get('Date', '')
    
    base_name = filename_override if filename_override else clean_title
    # Sanitize filename
    base_name = re.sub(r'[<>:"/\\|?*]', '', base_name)
    base_name = re.sub(r'\.mp3$', '', base_name, flags=re.IGNORECASE)
    
    # Subfolder logic
    save_dir = os.path.join(SCRIPT_DIR, "CueSheets")
    os.makedirs(save_dir, exist_ok=True)
    
    # Unique filename
    counter = 1
    final_base_name = base_name
    while os.path.exists(os.path.join(save_dir, f"{final_base_name}.cue")):
        final_base_name = f"{base_name} ({counter})"
        counter += 1
        
    output_path = os.path.join(save_dir, f"{final_base_name}.cue")
    audio_filename = f"{base_name}.mp3"

    # Build Content
    lines = []
    lines.append(f'PERFORMER "{clean_performer}"')
    lines.append(f'TITLE "{clean_title}"')
    if clean_date:
        lines.append(f'REM DATE "{clean_date}"')
    lines.append(f'FILE "{audio_filename}" MP3')
    
    for i, track in enumerate(data['Tracks'], 1):
        t_title = track['title'].replace('"', "'")
        t_artist = track['artist'].replace('"', "'")
        td = track['time']
        
        idx01 = format_timedelta(td)
        
        lines.append(f'  TRACK {i:02} AUDIO')
        lines.append(f'    TITLE "{t_title}"')
        lines.append(f'    PERFORMER "{t_artist}"')
        
        # Index 00 Logic (Previous track end)
        if i > 1:
            td_prev = td - timedelta(seconds=1)
            idx00 = format_timedelta(td_prev)
            lines.append(f'    INDEX 00 {idx00}')
            
        lines.append(f'    INDEX 01 {idx01}')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
        
    print(f"\033[92mSaved to: {output_path}\033[0m") # Green text

# --- MAIN ---
def main():
    config = get_config()
    default_dj = config.get('DefaultPerformer', '')
    last_mode = config.get('LastMode', '1')

    print("\033[96m--- PYTHON SERATO TO CUE V1.0 ---\033[0m")
    print("1. SERATO WEBSITE: Single Playlist URL")
    print("2. LOCAL CLIPBOARD: History Export")
    print("3. SERATO WEBSITE: Batch Profile Download")
    
    mode = input(f"Choose Mode (Default: {last_mode}): ").strip()
    if not mode: mode = last_mode
    
    performer_save = default_dj

    if mode == "3":
        profile_url = input("Paste Serato Profile URL (Enter for default): ").strip()
        if not profile_url: profile_url = "https://serato.com/playlists"
        
        try:
            resp = requests.get(profile_url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Find links that look like playlists
            # Logic: href contains /playlists/USER/
            user_part = profile_url.rstrip('/').split('/')[-1]
            links = set()
            
            for a in soup.find_all('a', href=True):
                href = a['href']
                if f"/playlists/{user_part}/" in href:
                    full_link = f"https://serato.com{href}" if href.startswith('/') else href
                    links.add(full_link)
            
            print(f"Found {len(links)} playlists.")
            for link in links:
                data = get_serato_playlist_web(link)
                if data: save_cue_file(data)

        except Exception as e:
            print(f"Error: {e}")

    elif mode == "1":
        url = input("Paste Playlist URL: ").strip()
        if url:
            data = get_serato_playlist_web(url)
            if data:
                fname = input(f"Enter Filename (Default: {data['Title']}): ").strip()
                save_cue_file(data, fname if fname else None)

    elif mode == "2":
        raw_text = pyperclip.paste()
        if not raw_text:
            print("Clipboard is empty!")
            return

        print(f"Loaded {len(raw_text.splitlines())} lines from clipboard.")
        data = parse_serato_history_clipboard(raw_text)
        
        if not data['Tracks']:
            print("No tracks found.")
            return

        p_prompt = f"Enter DJ Name (Default: {default_dj}): " if default_dj else "Enter DJ Name: "
        dj = input(p_prompt).strip()
        if not dj: dj = default_dj
        performer_save = dj
        
        data['Performer'] = dj
        data['Title'] = input("Enter Mix Title: ").strip()
        if not data['Date']:
            data['Date'] = input("Enter Date (dd/mm/yyyy): ").strip()
            
        fname = input("Enter Filename: ").strip()
        save_cue_file(data, fname)

    save_config(performer_save, mode)
    input("\nPress Enter to close...")

if __name__ == "__main__":
    main()