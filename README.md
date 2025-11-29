# 🎚️ Serato to CUE Generator

**A robust PowerShell automation tool to archive your DJ mixes.**

This tool converts **Serato Playlists** (from the web) and **Local History Exports** (via Clipboard) into perfect `.cue` files compatible with **MusicBee**, **VLC**, and **Foobar2000**.

---

## 🚀 Features

* **📋 Smart Clipboard Parser:** Intelligently handles Serato's "History Export" text format.
* **🕷️ Serato Web Scraper:** Downloads tracklist data directly from public Serato playlist URLs.
* **📦 Batch Mode:** Scans a Serato Profile page and downloads CUE files for all visible playlists.
* **💾 Auto-Config:** Remembers your DJ Name and preferred mode for a faster workflow (`config.json`).
* **🔤 UTF-8 Support:** Saves files without BOM, ensuring special characters (accents, emojis) work in older software.

---

## 🛠️ Installation

1.  **Download** the `makecue.ps1` file from this repository.
2.  Place it in a folder (e.g., `Documents\DJ Tools`).
3.  That's it! No external dependencies required (uses native Windows PowerShell).

---

## 📖 How to Use

Right-click `makecue.ps1` and select **Run with PowerShell**.

### 1. Single Playlist URL (Web)
* **Best for:** Archiving a specific mix you just uploaded.
* Paste any public Serato playlist URL.
* The script grabs the Artist, Title, and Date automatically.

### 2. Local Clipboard Import (Offline)
* **Best for:** Converting Serato "History" text exports (Text/CSV) or manual tracklists.
* **The "Smart Wrap" Feature:**
    * Even if your text file looks broken (e.g., Artist on line 1, Time on line 2), this script will detect it and stitch the lines back together.
* **Steps:**
    1.  Open Serato History / Text File.
    2.  Highlight the text and **Copy (Ctrl+C)**.
    3.  Run the script and select **Mode 2**.

### 3. Batch Profile Download
* **Best for:** Backing up recent mixes.
* Paste your main profile link (e.g., `https://serato.com/playlists/YOUR_NAME`).
* The script will scan the profile page and generate a unique `.cue` file for every playlist found.

---

## ⚙️ Configuration
The script creates a `config.json` file in the same folder after the first run.
* **DefaultPerformer:** Auto-fills your DJ name.
* **LastMode:** Remembers the last option you selected.
