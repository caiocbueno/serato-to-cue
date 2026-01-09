import re
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from utils import clean_text, get_track_artist_title

def parse_serato_history_clipboard(raw_text):
    lines = raw_text.splitlines()
    tracks = []
    mix_date = ""
    first_start_time = None
    time_pattern = r"(\d{1,2}:\d{2}:\d{2})"
    
    # 1. Tenta achar data no header
    for line in lines:
        date_match = re.search(r"(\d{2}/\d{2}/\d{4})", line)
        if date_match:
            mix_date = date_match.group(1)
            break
            
    line_buffer = ""
    
    for line in lines:
        line = line.strip()
        
        # Filtros
        if not line or line.startswith("-") or "Song" in line and "Start Time" in line:
            continue
        if re.match(r"^\d{2}/\d{2}/\d{4}.*\d{1,2}:\d{2}:\d{2}", line):
            continue

        time_matches = list(re.finditer(time_pattern, line))
        
        if time_matches:
            found_time_str = time_matches[0].group(1)
            
            # Limpa TODOS os horários da linha para não sujar o título
            text_part = re.sub(time_pattern, "", line).strip()
            full_track_string = f"{line_buffer} {text_part}".strip()
            line_buffer = ""
            
            # Lógica de separação de colunas (Tab > Espaços > Hífen)
            if "\t" in full_track_string:
                cols = [c.strip() for c in full_track_string.split("\t") if c.strip()]
            elif "  " in full_track_string:
                cols = re.split(r"\s{2,}", full_track_string)
            elif " - " in full_track_string:
                cols = full_track_string.split(" - ", 1)
            else:
                cols = [full_track_string]
            
            if len(cols) >= 2:
                title = cols[0]
                artist = cols[1]
            else:
                # Tenta fallback reverso ou padrão
                title = full_track_string
                artist = "Unknown"
                if " - " in full_track_string:
                     parts = full_track_string.split(" - ", 1)
                     artist = parts[0].strip()
                     title = parts[1].strip()

            if re.match(r"^\d{1,2}:\d{2}:\d{2}$", artist):
                artist = "Unknown"

            try:
                dt_format = "%H:%M:%S"
                if len(found_time_str.split(":")[0]) == 1: found_time_str = "0" + found_time_str
                curr_dt = datetime.strptime(found_time_str, dt_format)
                
                if first_start_time is None:
                    first_start_time = curr_dt
                    rel_time = timedelta(0)
                else:
                    rel_time = curr_dt - first_start_time
                    if rel_time.total_seconds() < 0: 
                         rel_time += timedelta(days=1)
                
                tracks.append({
                    'time': rel_time,
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
        
        title_tag = soup.find('title')
        raw_title = title_tag.text.replace(" - Serato DJ Playlists", "").strip() if title_tag else "Unknown Mix"
        performer = "Unknown DJ"
        
        if " - " in raw_title:
            parts = raw_title.split(" - ")
            performer = parts[-1].strip()
            album_title = " - ".join(parts[:-1]).strip()
        else:
            album_title = raw_title

        mix_date = ""
        date_elem = soup.find(class_='playlist-date')
        if date_elem: mix_date = date_elem.text.strip()
            
        tracks = []
        track_elements = soup.select('.playlist-track-container')
        
        if not track_elements:
            times = soup.select('.playlist-tracktime')
            for t in times:
                parent = t.find_parent('div')
                if parent: track_elements.append(parent)

        for row in track_elements:
            time_div = row.select_one('.playlist-tracktime')
            name_div = row.select_one('.playlist-trackname')
            
            if time_div and name_div:
                time_str = time_div.text.strip()
                full_name = name_div.text.strip()
                t_artist, t_title = get_track_artist_title(full_name)
                
                parts = list(map(int, time_str.split(':')))
                if len(parts) == 2:
                    td = timedelta(minutes=parts[0], seconds=parts[1])
                elif len(parts) == 3:
                    td = timedelta(hours=parts[0], minutes=parts[1], seconds=parts[2])
                else:
                    td = timedelta(0)

                tracks.append({'time': td, 'title': t_title, 'artist': t_artist})
                
        return {'Title': album_title, 'Performer': performer, 'Date': mix_date, 'Tracks': tracks}
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return None