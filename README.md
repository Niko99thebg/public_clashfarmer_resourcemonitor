# ClashFarmer Resource Monitor

A Python GUI application that monitors your resource levels in ClashFarmer using screen OCR, and stops the bot automatically when resource limits are reached. Telegram notifications are sent when limits are triggered.

![screenshot](preview.jpg) <!-- Optional: add screenshot image -->

---

## Features

- 🪄 Automatically reads Gold, Elixir, and Dark Elixir via OCR
- ⏱️ Custom check interval (in minutes)
- 📦 Stops ClashFarmer.exe when resource limits are reached
- 🛑 Option to stop when *any* or *all* resources reach their max
- 🔔 Sends a Telegram message when stopping
- 🔍 Optional debug mode with saved OCR image and text
- 💾 Configurable & settings saved between runs
- 🖼️ Easy-to-use GUI built with `tkinter`

---

## Requirements

- Python 3.9+
- Tesseract OCR installed and added to PATH
  (Directory: C:\Program Files\Tesseract-OCR)
  👉 [Download Tesseract](https://github.com/tesseract-ocr/tesseract)

---

## Installation

1. Download the latest release:

   👉 Go to the [Releases section](https://github.com/niko99thebg/public_clashfarmer_resourcemonitor/releases)  
   and download the latest `.zip` file.

2. Extract the folder.

3. Run `ClashFarmerMonitor.exe` without removing it from the folder.

---

## Telegram Integration

To receive Telegram alerts:

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Copy the bot token and paste it into the GUI
3. Click **"Register"** next to the "Telegram Chat ID" field to auto-detect your chat

---

## Configuration

All settings are saved in `config.json`.  
You can edit them via the GUI or manually in the file.

---

## License

This project is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).

You are free to use, modify, and distribute this software for personal or commercial use,
as long as you include proper attribution and comply with the terms of the license.

---

## Disclaimer

This tool interacts with ClashFarmer and uses OCR automation.  
Use at your own risk. I am not affiliated with [Clash of Clans](https://supercell.com/en/games/clashofclans/) or [ClashFarmer](https://www.clashfarmer.com).

---

## Author

Developed with ❤️ by Niko99thebg
