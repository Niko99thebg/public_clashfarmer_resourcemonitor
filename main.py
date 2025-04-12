import tkinter as tk
from tkinter import ttk, messagebox
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
from PIL import Image, ImageOps, ImageFilter, ImageEnhance

# Path to Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

text_log = None
CONFIG_FILE = "config.json"
running = False
debug_enabled = False

def save_config(data):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)
        log_message("Configuration saved.")
    except Exception as e:
        log_message(f"Error saving configuration: {e}")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            log_message("Configuration loaded.")
            return config
        except Exception as e:
            log_message(f"Error loading configuration: {e}")
    return {}

def list_windows():
    return [w for w in gw.getAllWindows() if w.title.strip() != ""]

def log_message(msg):
    global text_log, debug_enabled
    msg = str(msg).strip()
    if not debug_enabled:
        if not any(word in msg.lower() for word in ["error", "telegram", "reached", "started", "terminated", "found", "stopped"]):
            return
    print(msg)
    if text_log is not None:
        text_log.configure(state='normal')
        text_log.insert(tk.END, msg + "\n")
        text_log.see(tk.END)
        text_log.configure(state='disabled')

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
        log_message(f"Error capturing/cropping image: {e}")
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
        log_message(f"Found values: Gold={gold} - Elixir={elixir} - Dark Elixir={dark}")
        if require_all:
            return gold >= gold_max and elixir >= elixir_max and dark >= dark_elixir_max
        else:
            return gold >= gold_max or elixir >= elixir_max or dark >= dark_elixir_max
    else:
        if debug_enabled:
            log_message("Pattern not found in OCR text.")
    return False

def terminate_process():
    try:
        target_name = "ClashFarmer.exe"
        found = [proc for proc in psutil.process_iter(['pid', 'name']) if proc.info['name'] and target_name.lower() in proc.info['name'].lower()]
        if not found:
            log_message("ClashFarmer.exe not found.")
            return
        for proc in found:
            log_message(f"Attempting to terminate {proc.name()} (PID {proc.pid})")
            try:
                proc.terminate()
                proc.wait(timeout=5)
                log_message(f"{proc.name()} terminated.")
            except psutil.TimeoutExpired:
                log_message(f"{proc.name()} did not respond. Using kill().")
                proc.kill()
                proc.wait(timeout=3)
                log_message(f"{proc.name()} forcefully killed.")
            except Exception as e:
                log_message(f"Error terminating {proc.name()}: {e}")
    except Exception as e:
        log_message(f"General process termination error: {e}")

def send_telegram_message(bot_token, chat_id, message):
    try:
        if not chat_id.startswith("@") and not chat_id.lstrip("-").isdigit():
            log_message("Invalid chat ID: must be numeric.")
            return
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        response = requests.post(url, data={"chat_id": chat_id, "text": message})
        if response.status_code == 200:
            log_message(f"Telegram message sent to {chat_id}.")
        else:
            log_message(f"Telegram send error: {response.text}")
    except Exception as e:
        log_message(f"Telegram request error: {e}")

def register_telegram_user():
    token = entries.get("token")[0].get().strip()
    if not token:
        messagebox.showwarning("Missing Token", "Please enter your bot token first.")
        return
    def wait_for_message():
        log_message("Waiting for Telegram message...")
        messagebox.showinfo("Telegram Registration", "Send a message to your bot now.")
        start = time.time()
        while time.time() - start < 60:
            try:
                url = f"https://api.telegram.org/bot{token}/getUpdates"
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if "result" in data:
                        for update in reversed(data["result"]):
                            msg = update.get("message")
                            if msg and "chat" in msg and "id" in msg["chat"]:
                                chat_id = msg["chat"]["id"]
                                username = msg["chat"].get("username", "")
                                log_message(f"Received chat_id: {chat_id} (username: @{username})")
                                entries["chat_id"][0].delete(0, tk.END)
                                entries["chat_id"][0].insert(0, str(chat_id))
                                if entries["chat_id"][1].get():
                                    saved["chat_id"] = str(chat_id)
                                    save_config(saved)
                                return
                time.sleep(2)
            except Exception as e:
                log_message(f"Telegram registration error: {e}")
                break
        log_message("Timeout waiting for message.")

    threading.Thread(target=wait_for_message, daemon=True).start()
def update_buttons():
    if running:
        btn_start.config(state="disabled")
        btn_refresh.config(state="disabled")
        window_menu.config(state="disabled")
        btn_stop.config(state="normal")
    else:
        btn_start.config(state="normal")
        btn_refresh.config(state="normal")
        window_menu.config(state="readonly")
        btn_stop.config(state="disabled")

def start_monitoring():
    global running, debug_enabled
    if running:
        log_message("Monitoring already running.")
        return

    debug_enabled = debug_var.get()
    config = {}
    for key, (entry, chk_var) in entries.items():
        val = entry.get().strip()
        config[key] = val
        if chk_var.get():
            saved[key] = val
    config["all"] = all_var.get()
    saved["all"] = all_var.get()

    title = window_var.get().strip()
    windows = list_windows()
    window = next((w for w in windows if w.title == title), None)
    if not window:
        log_message("Error: window not found.")
        messagebox.showerror("Error", "Window not found. Please refresh or check title.")
        return

    save_config(saved)
    running = True
    update_buttons()
    threading.Thread(target=monitor_loop, args=(config, window), daemon=True).start()

def stop_monitoring():
    global running
    if running:
        running = False
        log_message("Monitoring stopped.")
        update_buttons()
    else:
        log_message("Monitoring is not running.")

def monitor_loop(config, window):
    global running
    log_message("Monitoring started.")
    while running:
        image = capture_window(window)
        if image is None:
            log_message("Invalid image, retrying in 5s...")
            time.sleep(5)
            continue
        text = read_text(image)
        log_message(f"OCR Text:\n{text}")
        try:
            if resource_condition(
                text,
                int(config["gold"]),
                int(config["elixir"]),
                int(config["dark_elixir"]),
                config.get("all", True)
            ):
                log_message("Condition met: max values reached.")
                terminate_process()
                send_telegram_message(config["token"], config["chat_id"], "Max resources reached. Window closed.")
                running = False
                update_buttons()
                break
            else:
                log_message("Condition not yet met.")
        except Exception as e:
            log_message(f"Error evaluating condition: {e}")
        time.sleep(float(config["interval"]) * 60)
    running = False
    update_buttons()
    log_message("Monitoring ended.")

def toggle_entry_state(chk_var, entry):
    if chk_var.get():
        entry.configure(state="disabled")
        log_message("Field saved and locked.")
    else:
        entry.configure(state="normal")
        log_message("Field unlocked for editing.")

# === GUI ===
root = tk.Tk()
root.title("ClashFarmer Resource Monitor")
root.geometry("800x600")

main_frame = ttk.Frame(root, padding=10)
main_frame.grid(row=0, column=0, sticky="nsew")
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=0)
main_frame.columnconfigure(1, weight=1)

saved = load_config()

fields = {
    "interval": "Check Interval (minutes)",
    "gold": "Gold Max",
    "elixir": "Elixir Max",
    "dark_elixir": "Dark Elixir Max",
    "token": "Telegram Bot Token",
    "chat_id": "Telegram Username/Chat ID"
}

entries = {}
row = 0
for key, label in fields.items():
    ttk.Label(main_frame, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=3)
    entry = ttk.Entry(main_frame)
    entry.grid(row=row, column=1, sticky="ew", padx=5, pady=3)

    if key == "chat_id":
        btn_register = ttk.Button(main_frame, text="Register", command=register_telegram_user)
        btn_register.grid(row=row, column=3, padx=5, pady=3)

    if key in saved:
        entry.insert(0, saved[key])
    var = tk.BooleanVar(value=(key in saved))
    chk = ttk.Checkbutton(main_frame, variable=var)
    chk.grid(row=row, column=2, padx=5, pady=3)
    var.trace_add("write", lambda *args, v=var, e=entry: toggle_entry_state(v, e))
    if var.get():
        entry.configure(state="disabled")
    entries[key] = (entry, var)
    row += 1

# Resource condition checkbox
all_var = tk.BooleanVar(value=saved.get("all", True))
ttk.Label(main_frame, text="Stop condition:").grid(row=row, column=0, sticky="w", padx=5, pady=3)
chk_all = ttk.Checkbutton(main_frame, text="All resources must be full", variable=all_var)
chk_all.grid(row=row, column=1, sticky="w", padx=5, pady=3)
row += 1

# Debug mode checkbox
debug_var = tk.BooleanVar(value=False)
chk_debug = ttk.Checkbutton(main_frame, text="Enable Debug Mode", variable=debug_var)
chk_debug.grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=5)
row += 1

# Window selection
ttk.Label(main_frame, text="Window to monitor:").grid(row=row, column=0, sticky="w", padx=5, pady=3)
window_var = tk.StringVar()
window_menu = ttk.Combobox(main_frame, textvariable=window_var, width=60)
window_menu['values'] = [w.title for w in list_windows()]
window_menu.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
row += 1

# Buttons
btn_start = ttk.Button(main_frame, text="Start", command=start_monitoring)
btn_start.grid(row=row, column=0, padx=5, pady=5, sticky="ew")
btn_stop = ttk.Button(main_frame, text="Stop", command=stop_monitoring)
btn_stop.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
btn_refresh = ttk.Button(main_frame, text="Refresh Windows",
                         command=lambda: window_menu.config(values=[w.title for w in list_windows()]))
btn_refresh.grid(row=row, column=2, padx=5, pady=5, sticky="ew")
row += 1

# Log area
log_frame = ttk.Frame(root, padding=10)
log_frame.grid(row=1, column=0, sticky="nsew")
root.rowconfigure(1, weight=1)
root.columnconfigure(0, weight=1)

text_log = tk.Text(log_frame, wrap="word", state="disabled")
text_log.grid(row=0, column=0, sticky="nsew")
scrollbar = ttk.Scrollbar(log_frame, command=text_log.yview)
scrollbar.grid(row=0, column=1, sticky="ns")
text_log.config(yscrollcommand=scrollbar.set)
log_frame.rowconfigure(0, weight=1)
log_frame.columnconfigure(0, weight=1)

log_message("Application started.")
update_buttons()
root.mainloop()
