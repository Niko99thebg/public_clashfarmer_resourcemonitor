import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage
import threading
import json
import time
import re
import os
import psutil
import requests
import pytesseract
import pyautogui
import pygetwindow as gw
import webbrowser
import subprocess
import win32gui
import win32con
from PIL import Image, ImageOps, ImageFilter, ImageEnhance, ImageDraw

import ctypes
def is_admin():
    return ctypes.windll.shell32.IsUserAnAdmin() != 0

version=2.1

pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

text_log = None
CONFIG_FILE = "config.json"
running = False
debug_enabled = False
entries = {}
saved = {}

def log_message(msg):
    global text_log, debug_enabled
    msg = str(msg).strip()

    # Quando debug è disattivato, non mostrare l'OCR text ma tutto il resto
    if not debug_enabled and msg.startswith("OCR Text:"):
        return

    print(msg)
    if text_log:
        text_log.configure(state="normal")
        text_log.insert(tk.END, msg + "\n")
        text_log.see(tk.END)
        text_log.configure(state="disabled")


def save_config_manual():
    config = {}
    for key, entry in entries.items():
        config[key] = entry.get().strip()
    config["all"] = all_var.get()
    saved.update(config)
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        log_message("Settings saved to config.json.")
        log_message("Settings saved.")
    except Exception as e:
        log_message(f"Error saving configuration: {e}")

def load_config():
    default_config = {
        "interval": "",
        "gold": "",
        "elixir": "",
        "dark_elixir": "",
        "token": "",
        "chat_id": "",
        "all": False
    }

    def write_default_config(reason):
        log_message(f"{reason} Creating new config.json with default values.")
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(default_config, f, indent=4)
            return default_config
        except Exception as e:
            log_message(f"Failed to create default config: {e}")
            return {}

    # 1. File non esiste
    if not os.path.exists(CONFIG_FILE):
        return write_default_config("No config file found.")

    # 2. File esiste ma può essere corrotto
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            log_message("Config loaded from config.json.")
            return config
    except Exception as e:
        return write_default_config(f"Error loading config file: {e}")


def register_telegram_user():
    token = entries.get("token").get().strip()
    if not token:
        messagebox.showwarning("Missing Token", "Please enter your bot token first.")
        return

    def wait_for_new_message():
        log_message("Waiting for a new Telegram message...")
        messagebox.showinfo("Telegram Registration", "Send a new message to your bot now.")

        try:
            # Step 1: get current update_id (the latest)
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            response = requests.get(url)
            last_update_id = None

            if response.status_code == 200:
                data = response.json()
                results = data.get("result", [])
                if results:
                    last_update_id = results[-1]["update_id"]

            # Step 2: poll for new messages with offset
            start_time = time.time()
            while time.time() - start_time < 60:
                offset_param = {"offset": last_update_id + 1} if last_update_id is not None else {}
                response = requests.get(url, params=offset_param)

                if response.status_code == 200:
                    data = response.json()
                    updates = data.get("result", [])
                    if updates:
                        for update in updates:
                            msg = update.get("message")
                            if msg and "chat" in msg and "id" in msg["chat"]:
                                chat_id = msg["chat"]["id"]
                                username = msg["chat"].get("username", "")
                                log_message(f"Received chat_id: {chat_id} (username: @{username})")
                                entries["chat_id"].delete(0, tk.END)
                                entries["chat_id"].insert(0, str(chat_id))
                                return
                time.sleep(2)

            log_message("Timeout: no new message received in 60 seconds.")
        except Exception as e:
            log_message(f"Telegram registration error: {e}")

    threading.Thread(target=wait_for_new_message, daemon=True).start()

def list_windows():
    return [w for w in gw.getAllWindows() if w.title.strip() != ""]

def preprocess_image(image):
    try:
        gray = image.convert("L")
        contrast = ImageEnhance.Contrast(gray).enhance(2.0)
        sharpened = contrast.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        return sharpened
    except Exception as e:
        log_message(f"Image preprocessing error: {e}")
        return image

def capture_window(window):
    try:
        bbox = (window.left, window.top, window.width, window.height)
        screenshot = pyautogui.screenshot(region=bbox)
        x_rel, y_rel, w_rel, h_rel = 0.0065, 0.083, 0.94, 0.60
        left = int(window.width * x_rel)
        top = int(window.height * y_rel)
        right = left + int(window.width * w_rel)
        bottom = top + int(window.height * h_rel)
        cropped = screenshot.crop((left, top, right, bottom))
        width, height = cropped.size
        cleaned = cropped.crop((1, 0, width - 1, height))
        processed = preprocess_image(cleaned)
        if debug_enabled:
            processed.save("debug_crop.png")
            log_message("Saved debug_crop.png")
        return processed
    except Exception as e:
        log_message(f"Error capturing window: {e}")
        return None

def read_text(image):
    try:
        text = pytesseract.image_to_string(image, config="--psm 6")
        if debug_enabled:
            with open("debug_text.txt", "w", encoding="utf-8") as f:
                f.write(text)
            log_message("Saved debug_text.txt")
        return text
    except Exception as e:
        log_message(f"OCR error: {e}")
        return ""

def resource_condition(text, gold_max, elixir_max, dark_elixir_max, require_all):
    pattern = r"Current Resources:\s*Gold:\s*(\d+)\s*Elixir:\s*(\d+)\s*Dark[_\s]?Elixir:\s*(\d+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        gold = int(match.group(1))
        elixir = int(match.group(2))
        dark = int(match.group(3))
        log_message(f"Found values: Gold={gold}, Elixir={elixir}, Dark Elixir={dark}")
        if require_all:
            return gold >= gold_max and elixir >= elixir_max and dark >= dark_elixir_max
        else:
            return gold >= gold_max or elixir >= elixir_max or dark >= dark_elixir_max
    elif debug_enabled:
        log_message("Pattern not found in OCR.")
    return False


# def terminate_process():
#     try:
#         target_name = "ClashFarmer.exe"
#         found = False
#
#         for proc in psutil.process_iter(['pid', 'name']):
#             if proc.info['name'] and target_name.lower() in proc.info['name'].lower():
#                 found = True
#                 log_message(f"Force killing {proc.name()} (PID {proc.pid}) and its children...")
#
#                 # Terminate child processes first
#                 for child in proc.children(recursive=True):
#                     try:
#                         if child.is_running():
#                             child.kill()
#                             try:
#                                 child.wait(timeout=3)
#                                 log_message(f"Child {child.name()} (PID {child.pid}) killed.")
#                             except psutil.TimeoutExpired:
#                                 if not child.is_running():
#                                     log_message(f"Child {child.name()} (PID {child.pid}) killed (wait timeout, but process exited).")
#                                 else:
#                                     raise
#                         else:
#                             log_message(f"Child {child.name()} (PID {child.pid}) was already terminated.")
#                     except Exception as e:
#                         log_message(f"Failed to kill child PID {child.pid}: {e}")
#
#                 # Terminate parent process
#                 try:
#                     if proc.is_running():
#                         proc.kill()
#                         try:
#                             proc.wait(timeout=3)
#                             log_message(f"{proc.name()} (PID {proc.pid}) killed.")
#                         except psutil.TimeoutExpired:
#                             if not proc.is_running():
#                                 log_message(f"{proc.name()} (PID {proc.pid}) killed (wait timeout, but process exited).")
#                             else:
#                                 raise
#                     else:
#                         log_message(f"{proc.name()} (PID {proc.pid}) was already terminated.")
#                 except Exception as e:
#                     log_message(f"Failed to kill {proc.name()} (PID {proc.pid}): {e}")
#
#         if not found:
#             log_message("ClashFarmer.exe not found.")
#     except Exception as e:
#         log_message(f"Error during process termination: {e}")

def run_dynamic_ahk_click(window):
    try:
        ahk_path = r"C:\Program Files\AutoHotkey\AutoHotkey.exe"  # ← verifica il percorso!
        hwnd = window._hWnd
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)

        # Coordinate: in basso a sinistra, leggermente più in alto
        click_x = left + 50
        click_y = bottom - 40 + 8

        ahk_code = f"""
        SetTitleMatchMode, 2
        CoordMode, Mouse, Screen
        WinActivate, ClashFarmer
        Sleep, 300
        DllCall("SetCursorPos", "int", {click_x}, "int", {click_y})
        Sleep, 150
        Click
        """

        with open("click_stop_bot.ahk", "w", encoding="utf-8") as f:
            f.write(ahk_code.strip())

        subprocess.Popen([ahk_path, "click_stop_bot.ahk"])
        log_message(f"AutoHotKey SINGLE click sent at ({click_x}, {click_y})")
        return True

    except Exception as e:
        log_message(f"Dynamic AHK error: {e}")
        return False

def send_telegram(bot_token, chat_id, message):
    try:
        if not chat_id.lstrip("-").isdigit():
            log_message("Invalid chat ID. Use numeric ID.")
            return
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        response = requests.post(url, data={"chat_id": chat_id, "text": message})
        if response.status_code == 200:
            log_message(f"Telegram message sent to {chat_id}.")
        else:
            log_message(f"Telegram error: {response.text}")
    except Exception as e:
        log_message(f"Telegram request error: {e}")

def update_input_state(enabled=True):
    state = "normal" if enabled else "disabled"
    for entry in entries.values():
        entry.configure(state=state)
    btn_save.config(state=state)

def start_monitoring():
    global running, debug_enabled
    if running:
        log_message("Monitoring already running.")
        return
    debug_enabled = debug_var.get()
    config = {k: v.get().strip() for k, v in entries.items()}
    config["all"] = all_var.get()
    title = window_var.get().strip()
    window = next((w for w in list_windows() if w.title == title), None)
    if not window:
        messagebox.showerror("Error", "Selected window not found.")
        return
    running = True
    update_input_state(False)
    btn_start.config(state="disabled")
    btn_refresh.config(state="disabled")
    btn_stop.config(state="normal")
    threading.Thread(target=monitor_loop, args=(config, window), daemon=True).start()

def stop_monitoring():
    global running
    running = False
    update_input_state(True)
    btn_start.config(state="normal")
    btn_refresh.config(state="normal")
    btn_stop.config(state="disabled")
    log_message("Monitoring stopped.")

def monitor_loop(config, window):
    global running
    log_message("Monitoring started.")

    try:
        delay = float(config.get("interval", 1))
        if delay <= 0:
            raise ValueError
    except ValueError:
        log_message("Invalid interval value. Defaulting to 1 minute.")
        delay = 1

    while running:
        image = capture_window(window)
        if image is None:
            log_message("Invalid image, retrying in 5s...")
            time.sleep(5)
            continue

        text = read_text(image)

        if debug_enabled:
            log_message(f"OCR Text:\n{text}")

        try:
            if resource_condition(
                text,
                int(config["gold"]),
                int(config["elixir"]),
                int(config["dark_elixir"]),
                config["all"]
            ):
                log_message("Condition met. Terminating.")
                run_dynamic_ahk_click(window)
                send_telegram(
                    config["token"],
                    config["chat_id"],
                    "Max resources reached. ClashFarmer closed."
                )
                stop_monitoring()
                break
            else:
                log_message("Condition not met.")
        except Exception as e:
            log_message(f"Error checking condition: {e}")

        time.sleep(delay * 60)

    log_message("Monitoring session ended.")


# === GUI ===
root = tk.Tk()
root.iconbitmap("icon.ico")
root.title(f"ClashFarmer Resource Monitor - Ver. {version}")
root.geometry("800x600")

# === Buttons icons
start_icon = PhotoImage(file="start_icon.png")
stop_icon = PhotoImage(file="stop_icon.png")
exit_icon = PhotoImage(file="exit_icon.png")
save_icon = PhotoImage(file="save_icon.png")
refresh_icon = PhotoImage(file="refresh_icon.png")


# === GRID CONFIG root
root.columnconfigure(0, weight=1)
root.rowconfigure(1, weight=1)  # log area
root.rowconfigure(2, weight=0)  # bottom buttons

# === MAIN FRAME
main_frame = ttk.Frame(root, padding=5)
main_frame.grid(row=0, column=0, sticky="nsew")
main_frame.columnconfigure(0, weight=0)
main_frame.columnconfigure(1, weight=1)

saved = load_config()
fields = {
    "interval": "Check Interval (minutes)",
    "gold": "Gold Max",
    "elixir": "Elixir Max",
    "dark_elixir": "Dark Elixir Max",
    "token": "Telegram Bot Token",
    "chat_id": "Telegram Chat ID"
}

entries.clear()
row = 0
for key, label in fields.items():
    ttk.Label(main_frame, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=5)

    if key == "chat_id":
        entry_frame = ttk.Frame(main_frame)
        entry_frame.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
        entry_frame.columnconfigure(0, weight=1)

        entry = ttk.Entry(entry_frame)
        entry.grid(row=0, column=0, sticky="ew")

        btn_register = ttk.Button(entry_frame, text="Register", command=register_telegram_user)
        btn_register.grid(row=0, column=1, padx=(5, 0))

    else:
        entry = ttk.Entry(main_frame)
        entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=5)

    entry.insert(0, saved.get(key, ""))
    entries[key] = entry
    row += 1

# All resources checkbox
all_var = tk.BooleanVar(value=saved.get("all", True))
ttk.Checkbutton(main_frame, text="All resources must reach the max \n(If not selected the bot will stop when one resource reaches the limit.)", variable=all_var)\
    .grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=5)
row += 1

# Save button (smaller)
btn_save = ttk.Button(main_frame, text="Save Settings", image=save_icon, compound="left", command=save_config_manual, width=20)
btn_save.image = save_icon  # to prevent garbage collection
btn_save.grid(row=row, column=0, padx=5, pady=5, sticky="w")
row += 1

# Debug mode
debug_var = tk.BooleanVar(value=False)
ttk.Checkbutton(main_frame, text="Enable Debug Mode\n(This will create debug logs and files)", variable=debug_var)\
    .grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=5)
row += 1

# Window selector + Refresh (responsive)
ttk.Label(main_frame, text="Window to monitor:").grid(row=row, column=0, sticky="w", padx=5, pady=5)

window_frame = ttk.Frame(main_frame)
window_frame.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
window_frame.columnconfigure(0, weight=1)

window_var = tk.StringVar()
window_menu = ttk.Combobox(window_frame, textvariable=window_var)
window_menu['values'] = [w.title for w in list_windows()]
window_menu.grid(row=0, column=0, sticky="ew")

btn_refresh = ttk.Button(window_frame, text="Refresh", image=refresh_icon, compound="left", command=lambda: window_menu.config(values=[w.title for w in list_windows()]))
btn_refresh.image = refresh_icon  # to prevent garbage collection
btn_refresh.grid(row=0, column=1, padx=(5, 0))
row += 1

# === LOG FRAME
log_frame = ttk.Frame(root, padding=5)
log_frame.grid(row=1, column=0, sticky="nsew")
log_frame.columnconfigure(0, weight=1)
log_frame.rowconfigure(0, weight=1)

text_log = tk.Text(log_frame, wrap="word", state="disabled")
text_log.grid(row=0, column=0, sticky="nsew", padx=(0, 0), pady=(0, 0))

scrollbar = ttk.Scrollbar(log_frame, command=text_log.yview)
scrollbar.grid(row=0, column=1, sticky="ns")
text_log.config(yscrollcommand=scrollbar.set)

# === BOTTOM LEFT BUTTONS (Start / Stop)
bottom_left_frame = ttk.Frame(root, padding=5)
bottom_left_frame.grid(row=2, column=0, sticky="w")
bottom_left_frame.columnconfigure(0, weight=0)
bottom_left_frame.columnconfigure(1, weight=0)

btn_start = ttk.Button(bottom_left_frame, text="Start", image=start_icon, compound="left", command=start_monitoring, width=15)
btn_start.image = start_icon  # to prevent garbage collection
btn_start.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")

btn_stop = ttk.Button(bottom_left_frame, text="Stop", image=stop_icon, compound="left", command=stop_monitoring, width=15, state="disabled")
btn_stop.image = stop_icon  # to prevent garbage collection
btn_stop.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="w")

# === BOTTOM RIGHT BUTTONS (Github + Exit)
def open_github():
    webbrowser.open_new("https://github.com/Niko99thebg/public_clashfarmer_resourcemonitor")

def exit_app():
    global running
    running = False
    root.quit()
    root.destroy()

bottom_right_frame = ttk.Frame(root, padding=5)
bottom_right_frame.grid(row=2, column=0, sticky="e")

btn_github = ttk.Button(bottom_right_frame, text="Github Project", command=open_github)
btn_github.pack(side="left", padx=(0, 5))

btn_exit = ttk.Button(bottom_right_frame, text="Exit", image=exit_icon, compound="left", command=exit_app)
btn_exit.image = exit_icon  # to prevent garbage collection
btn_exit.pack(side="left")

# === RUN LOOP
log_message("Application started.")
if not is_admin():
    messagebox.showwarning("Permission", "Please run this script as Administrator.")
    root.quit()
    root.destroy()
root.mainloop()