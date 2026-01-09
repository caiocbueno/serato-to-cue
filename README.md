# 🎚️ Serato to CUE Generator (Python Edition)

**A robust, cross-platform Python tool to archive your DJ mixes.**

This tool converts **Serato Playlists** (from the web) and **Local History Exports** (via Clipboard) into perfect `.cue` files compatible with **MusicBee**, **VLC**, and **Foobar2000**.

Now rewritten in Python for better performance, stability, and compatibility with Windows, macOS, and Linux.

---

## 🚀 Features

* **🐍 Python Powered:** Runs natively on Windows, macOS, and Linux.
* **📋 Smart Clipboard Parser:** Intelligently handles Serato's "History Export" text format, automatically cleaning up timestamps and formatting issues.
* **🕷️ Robust Web Scraper:** Uses `BeautifulSoup` to reliably download tracklist data from public Serato playlist URLs, even if the site layout shifts slightly.
* **📦 Batch Mode:** Scans a Serato Profile page and downloads CUE files for all visible playlists in one go.
* **💾 Auto-Config:** Remembers your DJ Name and preferred mode for a faster workflow (`config.json`).
* **📂 Modular Structure:** Clean code architecture split into logic modules for easy maintenance.

---

## 🛠️ Installation

### Prerequisites
* **Python 3.x** installed on your system.

### Quick Setup

1. **Clone or Download** this repository to a folder (e.g., `Documents/DJ Tools`).
2. Open your terminal in that folder.
3. (Optional but recommended) **Create a virtual environment**:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate
   ```
4. **Install dependencies** using the provided file:
   ```bash
   pip install -r requirements.txt
   ```
> **🐧 Linux Users:** You may need to install a clipboard utility:
   > `sudo apt install xclip` or `sudo pacman -S xclip`

---

## 📖 How to Use

Ensure your virtual environment is active (if you created one), then run the main script:

```bash
python serato2cue.py
```

### 1. Single Playlist URL (Web)
* **Best for:** Archiving a specific mix you just uploaded.
* Paste any public Serato playlist URL.
* The script grabs the Artist, Title, and Date automatically.

### 2. Local Clipboard Import (Offline)
* **Best for:** Converting Serato "History" text exports (Text/CSV) or manual tracklists.
* **How to use:**
    1. Open Serato History or your text export file.
    2. Highlight the text and **Copy (Ctrl+C)**.
    3. Run the script and select **Mode 2**.
    4. The script will read your clipboard, clean up the formatting, and generate the CUE file.

### 3. Batch Profile Download
* **Best for:** Backing up recent mixes or migrating your library.
* Paste your main profile link (e.g., `https://serato.com/playlists/YOUR_NAME`).
* The script will scan the profile page and generate a unique `.cue` file for every playlist found automatically.

---

## ⚙️ Configuration
The script creates a `config.json` file in the same folder after the first run.
* **DefaultPerformer:** Auto-fills your DJ name on next launch.
* **LastMode:** Remembers the last option you selected.

---

## 📂 Project Structure

* `serato2cue.py`: The entry point of the application.
* `parsers.py`: Logic for web scraping and clipboard text processing.
* `generator.py`: Logic for creating the .cue files.
* `utils.py`: Helper functions and configuration management.