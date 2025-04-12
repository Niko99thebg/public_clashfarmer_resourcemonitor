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

# Percorso Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

text_log = None
CONFIG_FILE = "config.json"
running = False
debug_attivo = False  # variabile globale

def salva_config(dati):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(dati, f)
        log_message("Configurazione salvata.")
    except Exception as e:
        log_message(f"Errore nel salvataggio della configurazione: {e}")

def carica_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            log_message("Configurazione caricata.")
            return config
        except Exception as e:
            log_message(f"Errore nel caricamento della configurazione: {e}")
    return {}

def lista_finestre():
    finestre = gw.getAllWindows()
    return [w for w in finestre if w.title.strip() != ""]

def log_message(msg):
    global text_log, debug_attivo
    msg = str(msg).strip()
    if not debug_attivo:
        # Mostra solo messaggi importanti
        if not any(word in msg.lower() for word in ["errore", "telegram", "soddisfatta", "avviato", "terminato", "trovati", "fermata"]):
            return
    print(msg)
    if text_log is not None:
        text_log.configure(state='normal')
        text_log.insert(tk.END, msg + "\n")
        text_log.see(tk.END)
        text_log.configure(state='disabled')

def pre_elabora_immagine(image):
    try:
        gray = image.convert("L")
        contrast = ImageEnhance.Contrast(gray).enhance(2.0)
        sharpened = contrast.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        return sharpened
    except Exception as e:
        log_message(f"Errore nel pre-processing immagine: {e}")
        return image

def cattura_finestra(window):
    try:
        bbox = (window.left, window.top, window.width, window.height)
        screenshot_full = pyautogui.screenshot(region=bbox)

        x_rel, y_rel, w_rel, h_rel = 0.0065, 0.083, 0.94, 0.60
        left = int(window.width * x_rel)
        top = int(window.height * y_rel)
        right = left + int(window.width * w_rel)
        bottom = top + int(window.height * h_rel)

        cropped = screenshot_full.crop((left, top, right, bottom))
        width, height = cropped.size
        cropped_clean = cropped.crop((1, 0, width - 1, height))  # margine 1px

        processed = pre_elabora_immagine(cropped_clean)
        if debug_attivo:
            processed.save("debug_crop.png")
            log_message("Immagine salvata in debug_crop.png")
        return processed
    except Exception as e:
        log_message(f"Errore nel catturare/ritagliare l'immagine: {e}")
        return None

def leggi_testo(image):
    try:
        text = pytesseract.image_to_string(image, config="--psm 6")
        if debug_attivo:
            with open("debug_text.txt", "w", encoding="utf-8") as f:
                f.write(text)
            log_message("OCR salvato in debug_text.txt")
        return text
    except Exception as e:
        log_message(f"Errore OCR: {e}")
        return ""

def condizione_risorse(text, gold_max, elixir_max, dark_elixir_max, tutte):
    pattern = r"Current Resources:\s*Gold:\s*(\d+)\s*Elixir:\s*(\d+)\s*Dark[_\s]?Elixir:\s*(\d+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        gold = int(match.group(1))
        elixir = int(match.group(2))
        dark = int(match.group(3))
        log_message(f"Valori trovati: Gold={gold} - Elixir={elixir} - Dark Elixir={dark}")
        if tutte:
            return (gold >= gold_max and elixir >= elixir_max and dark >= dark_elixir_max)
        else:
            return (gold >= gold_max or elixir >= elixir_max or dark >= dark_elixir_max)
    else:
        if debug_attivo:
            log_message("Pattern non trovato nel testo OCR.")
    return False

def termina_processo(_window=None):
    try:
        target_name = "ClashFarmer.exe"
        trovati = []

        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and target_name.lower() in proc.info['name'].lower():
                trovati.append(proc)

        if not trovati:
            log_message("Nessun processo ClashFarmer.exe trovato.")
            return

        for proc in trovati:
            log_message(f"Tentativo di terminare {proc.name()} (PID {proc.pid})")
            try:
                proc.terminate()
                proc.wait(timeout=5)
                log_message(f"{proc.name()} terminato correttamente.")
            except psutil.TimeoutExpired:
                log_message(f"{proc.name()} non ha risposto a terminate(). Uso kill()...")
                proc.kill()
                proc.wait(timeout=3)
                log_message(f"{proc.name()} forzatamente terminato con kill().")
            except Exception as e:
                log_message(f"Errore nel terminare {proc.name()} (PID {proc.pid}): {e}")
    except Exception as e:
        log_message(f"Errore generale nella terminazione del processo: {e}")

def invia_messaggio(bot_token, chat_id, msg):
    try:
        if not chat_id.startswith("@") and not chat_id.lstrip("-").isdigit():
            log_message("Attenzione: Il campo 'Telegram username' deve iniziare con @ oppure essere numerico.")
            return

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        response = requests.post(url, data={"chat_id": chat_id, "text": msg})
        if response.status_code == 200:
            log_message(f"Messaggio Telegram inviato a {chat_id}.")
        else:
            log_message(f"Errore invio Telegram: {response.text}")
    except Exception as e:
        log_message(f"Errore richiesta Telegram: {e}")

def registra_telegram_username():
    token_entry = entries.get("token")[0].get().strip()
    if not token_entry:
        messagebox.showwarning("Token mancante", "Inserisci prima il token Telegram.")
        return

    def attesa_messaggio():
        log_message("Attesa di un messaggio Telegram per registrazione...")
        messagebox.showinfo("Registrazione", "Ora scrivi un messaggio al bot su Telegram.")

        start_time = time.time()
        while time.time() - start_time < 60:
            try:
                url = f"https://api.telegram.org/bot{token_entry}/getUpdates"
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if "result" in data:
                        for update in reversed(data["result"]):
                            msg = update.get("message")
                            if msg and "chat" in msg and "id" in msg["chat"]:
                                chat_id = msg["chat"]["id"]
                                username = msg["chat"].get("username", "")
                                log_message(f"Chat ID ricevuto: {chat_id} (username: @{username})")
                                entries["chat_id"][0].delete(0, tk.END)
                                entries["chat_id"][0].insert(0, str(chat_id))
                                if entries["chat_id"][1].get():
                                    salvati["chat_id"] = str(chat_id)
                                    salva_config(salvati)
                                return
                time.sleep(2)
            except Exception as e:
                log_message(f"Errore durante la registrazione Telegram: {e}")
                break
        log_message("Timeout: nessun messaggio ricevuto entro 60 secondi.")

    threading.Thread(target=attesa_messaggio, daemon=True).start()
def aggiorna_stato_bottoni():
    if running:
        btn_avvia.config(state="disabled")
        btn_aggiorna.config(state="disabled")
        finestra_menu.config(state="disabled")
        btn_ferma.config(state="normal")
    else:
        btn_avvia.config(state="normal")
        btn_aggiorna.config(state="normal")
        finestra_menu.config(state="readonly")
        btn_ferma.config(state="disabled")

def monitoraggio(config, window):
    global running
    log_message("Monitoraggio avviato.")
    while running:
        image = cattura_finestra(window)
        if image is None:
            log_message("Immagine non valida, riprovo tra 5 secondi...")
            time.sleep(5)
            continue
        testo = leggi_testo(image)
        log_message(f"Testo OCR:\n{testo}")
        try:
            if condizione_risorse(
                testo,
                int(config["gold"]),
                int(config["elixir"]),
                int(config["dark_elixir"]),
                config.get("tutte", True)
            ):
                log_message("Condizione soddisfatta: valori raggiunti.")
                termina_processo()
                invia_messaggio(config["token"], config["chat_id"], "Valori massimi raggiunti: finestra terminata.")
                running = False
                aggiorna_stato_bottoni()
                break
            else:
                log_message("Condizione non ancora soddisfatta.")
        except Exception as e:
            log_message(f"Errore nella valutazione della condizione: {e}")
        time.sleep(float(config["intervallo"]) * 60)
    running = False
    aggiorna_stato_bottoni()
    log_message("Monitoraggio terminato.")

def avvia_script():
    global running, debug_attivo
    if running:
        log_message("Il monitoraggio è già in esecuzione.")
        return

    debug_attivo = debug_var.get()

    config = {}
    for key, (entry, chk_var) in entries.items():
        val = entry.get().strip()
        config[key] = val
        if chk_var.get():
            salvati[key] = val

    config["tutte"] = tutte_var.get()
    salvati["tutte"] = tutte_var.get()

    window_title = finestra_var.get().strip()
    finestre = lista_finestre()
    window = next((w for w in finestre if w.title == window_title), None)
    if not window:
        log_message("Errore: finestra non trovata.")
        messagebox.showerror("Errore", "Finestra non trovata. Aggiorna la lista o controlla il titolo.")
        return

    salva_config(salvati)
    running = True
    aggiorna_stato_bottoni()
    threading.Thread(target=monitoraggio, args=(config, window), daemon=True).start()

def ferma_script():
    global running
    if running:
        running = False
        log_message("Richiesta di fermata del monitoraggio.")
        aggiorna_stato_bottoni()
    else:
        log_message("Il monitoraggio non è in esecuzione.")

def aggiorna_stato_entry(chk_var, entry):
    if chk_var.get():
        entry.configure(state="disabled")
        log_message("Campo salvato e bloccato.")
    else:
        entry.configure(state="normal")
        log_message("Campo sbloccato per modifiche.")

# === GUI ===
root = tk.Tk()
root.title("Monitoraggio Risorse - GUI")
root.geometry("800x600")

main_frame = ttk.Frame(root, padding=10)
main_frame.grid(row=0, column=0, sticky="nsew")
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=0)
main_frame.columnconfigure(1, weight=1)

salvati = carica_config()

campi = {
    "intervallo": "Intervallo (minuti)",
    "gold": "Gold max",
    "elixir": "Elixir max",
    "dark_elixir": "Dark Elixir max",
    "token": "Token Telegram",
    "chat_id": "Telegram username"
}

entries = {}
row = 0
for key, label in campi.items():
    ttk.Label(main_frame, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=3)
    entry = ttk.Entry(main_frame)
    entry.grid(row=row, column=1, sticky="ew", padx=5, pady=3)

    if key == "chat_id":
        btn_reg = ttk.Button(main_frame, text="Registrati", command=registra_telegram_username)
        btn_reg.grid(row=row, column=3, padx=5, pady=3)

    if key in salvati:
        entry.insert(0, salvati[key])
    var = tk.BooleanVar(value=(key in salvati))
    chk = ttk.Checkbutton(main_frame, variable=var)
    chk.grid(row=row, column=2, padx=5, pady=3)
    var.trace_add("write", lambda *args, chk_var=var, ent=entry: aggiorna_stato_entry(chk_var, ent))
    if var.get():
        entry.configure(state="disabled")
    entries[key] = (entry, var)
    row += 1

tutte_var = tk.BooleanVar(value=salvati.get("tutte", True))
ttk.Label(main_frame, text="Condizione risorse:").grid(row=row, column=0, sticky="w", padx=5, pady=3)
chk_tutte = ttk.Checkbutton(main_frame, text="Tutte le risorse al massimo", variable=tutte_var)
chk_tutte.grid(row=row, column=1, sticky="w", padx=5, pady=3)
row += 1

debug_var = tk.BooleanVar(value=False)
chk_debug = ttk.Checkbutton(main_frame, text="Modalità Debug", variable=debug_var)
chk_debug.grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=5)
row += 1

ttk.Label(main_frame, text="Finestra da monitorare:").grid(row=row, column=0, sticky="w", padx=5, pady=3)
finestra_var = tk.StringVar()
finestra_menu = ttk.Combobox(main_frame, textvariable=finestra_var, width=60)
finestra_menu['values'] = [w.title for w in lista_finestre()]
finestra_menu.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
row += 1

btn_avvia = ttk.Button(main_frame, text="Avvia", command=avvia_script)
btn_avvia.grid(row=row, column=0, padx=5, pady=5, sticky="ew")
btn_ferma = ttk.Button(main_frame, text="Ferma", command=ferma_script)
btn_ferma.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
btn_aggiorna = ttk.Button(main_frame, text="Aggiorna Finestre",
                          command=lambda: finestra_menu.config(values=[w.title for w in lista_finestre()]))
btn_aggiorna.grid(row=row, column=2, padx=5, pady=5, sticky="ew")
row += 1

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
aggiorna_stato_bottoni()
root.mainloop()
