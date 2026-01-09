import os
import re
from datetime import timedelta
from utils import SCRIPT_DIR, format_timedelta

def save_cue_file(data, filename_override=None):
    if not data or not data.get('Tracks'):
        print("No tracks to save.")
        return

    clean_performer = data.get('Performer', 'Unknown').replace('"', "'")
    clean_title = data.get('Title', 'Unknown').replace('"', "'")
    clean_date = data.get('Date', '')
    
    base_name = filename_override if filename_override else clean_title
    base_name = re.sub(r'[<>:"/\\|?*]', '', base_name)
    base_name = re.sub(r'\.mp3$', '', base_name, flags=re.IGNORECASE)
    
    save_dir = os.path.join(SCRIPT_DIR, "CueSheets")
    os.makedirs(save_dir, exist_ok=True)
    
    counter = 1
    final_base_name = base_name
    while os.path.exists(os.path.join(save_dir, f"{final_base_name}.cue")):
        final_base_name = f"{base_name} ({counter})"
        counter += 1
        
    output_path = os.path.join(save_dir, f"{final_base_name}.cue")
    audio_filename = f"{base_name}.mp3"

    lines = []
    lines.append(f'PERFORMER "{clean_performer}"')
    lines.append(f'TITLE "{clean_title}"')
    if clean_date: lines.append(f'REM DATE "{clean_date}"')
    lines.append(f'FILE "{audio_filename}" MP3')
    
    for i, track in enumerate(data['Tracks'], 1):
        t_title = track['title'].replace('"', "'")
        t_artist = track['artist'].replace('"', "'")
        td = track['time']
        
        idx01 = format_timedelta(td)
        
        lines.append(f'  TRACK {i:02} AUDIO')
        lines.append(f'    TITLE "{t_title}"')
        lines.append(f'    PERFORMER "{t_artist}"')
        
        if i > 1:
            td_prev = td - timedelta(seconds=1)
            idx00 = format_timedelta(td_prev)
            lines.append(f'    INDEX 00 {idx00}')
            
        lines.append(f'    INDEX 01 {idx01}')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
        
    print(f"\033[92mSaved to: {output_path}\033[0m")