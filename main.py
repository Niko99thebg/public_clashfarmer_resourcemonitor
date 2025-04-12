import time
import re
import sys
import psutil
import requests
import pygetwindow as gw
from PIL import Image
import pytesseract
import pyautogui


# Se Tesseract non è nel PATH, specificare il percorso
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\nicol\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

def lista_finestre():
    """
    Ritorna una lista di tutte le finestre aperte con un titolo non vuoto.
    """
    windows = gw.getAllWindows()
    finestre = [w for w in windows if w.title.strip() != ""]
    return finestre


def seleziona_finestra():
    """
    Visualizza un elenco numerato delle finestre aperte e chiede all'utente di scegliere quella da monitorare.
    Restituisce la finestra selezionata o None se l'utente non ha fatto una scelta valida.
    """
    finestre = lista_finestre()
    if not finestre:
        print("Nessuna finestra aperta trovata.")
        return None

    print("Finestre aperte:")
    for i, finestra in enumerate(finestre, start=1):
        print(f"{i}. {finestra.title}")

    try:
        scelta = int(input("Inserisci il numero della finestra da monitorare: "))
        if 1 <= scelta <= len(finestre):
            return finestre[scelta - 1]
        else:
            print("Scelta non valida.")
            return None
    except ValueError:
        print("Inserisci un numero valido.")
        return None


def cattura_finestra(window):
    """Cattura lo screenshot dell'intera finestra."""
    # Ottieni le coordinate della finestra (left, top, width, height)
    bbox = (window.left, window.top, window.width, window.height)
    screenshot = pyautogui.screenshot(region=bbox)
    return screenshot


def leggi_testo_da_immagine(image):
    """Estrae il testo dall'immagine usando OCR."""
    return pytesseract.image_to_string(image)


def condizione_risorse(test_text, gold_max, elixir_max, dark_elixir_max):
    """
    Verifica se nel testo sono presenti le righe 'Current Resources:'
    e i valori massimi per Gold, Elixir e Dark_Elixir.
    """
    # Pattern per trovare le righe con i valori
    pattern = (r"Current Resources:\s*"
               r"Gold:\s*(\d+)\s*"
               r"Elixir:\s*(\d+)\s*"
               r"Dark[_\s]?Elixir:\s*(\d+)")
    match = re.search(pattern, test_text, re.IGNORECASE | re.MULTILINE)
    if match:
        gold_val = int(match.group(1))
        elixir_val = int(match.group(2))
        dark_elixir_val = int(match.group(3))
        print(f"Valori trovati: Gold={gold_val}, Elixir={elixir_val}, Dark Elixir={dark_elixir_val}")
        # Confronta i valori trovati con quelli massimi impostati
        if gold_val == gold_max and elixir_val == elixir_max and dark_elixir_val == dark_elixir_max:
            return True
    return False


def termina_processo(window):
    """Termina il processo associato alla finestra."""
    try:
        # Usando win32gui e win32process per ottenere il PID della finestra
        import win32gui, win32process
        hwnd = window._hWnd  # handle della finestra
        tid, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=5)
        print(f"Processo {proc.pid} terminato.")
    except Exception as e:
        print("Errore nella terminazione del processo:", e)


def invia_messaggio_telegram(bot_token, chat_id, messaggio):
    """Invia un messaggio Telegram usando il bot token e il chat_id."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": messaggio
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("Messaggio Telegram inviato correttamente.")
        else:
            print("Errore nell'invio del messaggio Telegram:", response.text)
    except Exception as e:
        print(f"Errore durante la richiesta a Telegram: {e}")


def main():
    # Selezione della finestra da monitorare
    window = None
    while window is None:
        window = seleziona_finestra()
        if window is None:
            print("Riprova la selezione della finestra.")

    print(f"Finestra selezionata: {window.title}")

    # Input dell'intervallo e dei valori massimi
    try:
        intervallo = float(input("Inserisci l'intervallo (in minuti) tra un controllo e l'altro: "))
        gold_max = int(input("Inserisci il valore massimo per Gold: "))
        elixir_max = int(input("Inserisci il valore massimo per Elixir: "))
        dark_elixir_max = int(input("Inserisci il valore massimo per Dark Elixir: "))
    except ValueError:
        print("Input non valido. Termino il programma.")
        sys.exit(1)

    bot_token = input("Inserisci il token del bot Telegram: ")
    chat_id = input("Inserisci il chat_id (o username) per ricevere il messaggio Telegram: ")

    while True:
        # Cattura lo screenshot della finestra
        screenshot = cattura_finestra(window)
        # Leggi il testo usando OCR
        testo = leggi_testo_da_immagine(screenshot)
        print("Testo OCR rilevato:\n", testo)

        # Verifica la condizione sui valori massimi
        if condizione_risorse(testo, gold_max, elixir_max, dark_elixir_max):
            print("Condizione soddisfatta: valori massimi trovati.")

            # Termina il processo associato alla finestra
            termina_processo(window)

            # Invia il messaggio Telegram
            messaggio = "Il processo associato alla finestra è stato terminato perché i valori massimi sono stati raggiunti."
            invia_messaggio_telegram(bot_token, chat_id, messaggio)

            break
        else:
            print("Condizione non ancora soddisfatta. Prossimo controllo tra {} minuti...".format(intervallo))

        time.sleep(intervallo * 60)


if __name__ == "__main__":
    main()
