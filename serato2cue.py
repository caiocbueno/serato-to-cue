import sys
import requests
from bs4 import BeautifulSoup
import pyperclip

# Importa os módulos locais
from utils import get_config, save_config
from parsers import get_serato_playlist_web, parse_serato_history_clipboard
from generator import save_cue_file

def main():
    config = get_config()
    default_dj = config.get('DefaultPerformer', '')
    last_mode = config.get('LastMode', '1')

    print("\033[96m--- PYTHON SERATO TO CUE V1.1 (Modular) ---\033[0m")
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