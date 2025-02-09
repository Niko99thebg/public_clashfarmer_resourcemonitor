#TODO: Integrazione con telegram per fermare il bot anzichè terminare il processo, fattibile con un altro bot che contatta il bot di clashfarmer?
import win32gui
import pyautogui
#from PIL import Image     capire se serve veramente
import numpy as np
import easyocr
import re
import time

import coloredlogs, logging

#Log settings
log = logging.getLogger(__name__)

fieldstyle = {'asctime': {'color': 'green'},
              'levelname': {'bold': True, 'color': 'black'},
              'filename':{'color':'cyan'},
              'funcName':{'color':'magenta'}}

levelstyles = {'critical': {'bold': True, 'color': 'red'},
               'debug': {'color': 'green'},
               'error': {'color': 'red'},
               'info': {'color':'white'},
               'warning': {'color': 'yellow'}}

coloredlogs.install(level=logging.INFO,
                    logger=log,
                    fmt='%(asctime)s [%(levelname)s] - [%(filename)s > %(funcName)s() > %(lineno)s] - %(message)s',
                    datefmt=' %Y/%m/%d %H:%M:%S',
                    field_styles=fieldstyle,
                    level_styles=levelstyles
                    )

loggingfile = logging.FileHandler("logs.log")
fileformat = logging.Formatter("%(asctime)s [%(levelname)s] - [%(filename)s > %(funcName)s() > %(lineno)s] - %(message)s")
loggingfile.setFormatter(fileformat)

loggingfile.setStream(open('logs.log', 'a', encoding='utf-8'))

log.addHandler(loggingfile)

def visibleCheck():
    def callback(hwnd, windows_list):
        title = win32gui.GetWindowText(hwnd)
        if win32gui.IsWindowVisible(hwnd) and title.strip():
            windows_list.append((hwnd, title))

    windows = []
    win32gui.EnumWindows(callback, windows)
    return windows

def filterer(windows):
    return [
        (hwnd, title) for hwnd, title in windows if len(title) > 2
    ]

def chooseWindow(windows):
    print("Opened windows:")
    for idx, (_, title) in enumerate(windows):
        print(f"{idx + 1}: {title}")

    while True:
        try:
            choice = int(input("\nChoose the number of ClashFarmer: "))
            if 1 <= choice <= len(windows):
                return windows[choice - 1]
            else:
                log.warning("Please choose a number on your screen")
        except ValueError:
            log.warning("Please pick a number, not letter or symbol")

def captureWindow(hwnd):
    rect = win32gui.GetWindowRect(hwnd)
    bbox = (rect[0], rect[1], rect[2], rect[3])
    return pyautogui.screenshot(region=bbox)

def textExtract(text):
    match = re.search(r'\d[\d,]*', text)
    if match:
        return int(match.group(0).replace(',', ''))
    return None

def resourceExtract(image):
    image_array = np.array(image)
    reader = easyocr.Reader(['en'], gpu=False)
    results = reader.readtext(image_array, detail=0)

    resources = {"gold": None, "elixir": None, "dark_elixir": None}

    for text in results:
        text_lower = text.lower()

        if resources["gold"] is None and "gold" in text_lower:
            resources["gold"] = textExtract(text)
        elif resources["elixir"] is None and "elixir" in text_lower and "dark" not in text_lower:
            resources["elixir"] = textExtract(text)
        elif resources["dark_elixir"] is None and ("dark elixir" in text_lower or "dark_elixir" in text_lower):
            resources["dark_elixir"] = textExtract(text)

        if all(value is not None for value in resources.values()):
            break

    return resources

def main():
    print("\nLooking for ClashFarmer")
    windows = visibleCheck()
    app_windows = filterer(windows)

    if not app_windows:
        log.warning("ClashFarmer not found, make sure it's open and visible on the screen\n")
        return

    selected_window = chooseWindow(app_windows)
    hwnd, title = selected_window
    print(f"Selected window: {title}")

    maxGold = int(input("Enter your max gold amount: "))
    maxElixir = int(input("Enter your max elixir amount: "))
    maxDark = int(input("Enter your max dark elixir amount: "))

    while True:
        screenshot = captureWindow(hwnd)
        if screenshot:
            print("\nExtracting resources...")
            resources = resourceExtract(screenshot)
            print("\nExtracted Resources:")
            for resource, value in resources.items():
                print(f"{resource.capitalize()}: {value if value is not None else 'Not Found'}")

            if (resources["gold"] is not None and resources["gold"] >= maxGold and
                resources["elixir"] is not None and resources["elixir"] >= maxElixir and
                resources["dark_elixir"] is not None and resources["dark_elixir"] >= maxDark):
                print("All storages full, closing ClashFarmer...\n")
                try:
                    win32gui.PostMessage(hwnd, 0x0010, 0, 0)
                    print("ClashFarmer closed")
                except Exception as e:
                    log.error(f"Failed to close ClashFarmer: {e}")
                break
            else:
                print("Storages not yet full, will keep retrying\n")
        else:
            print("Please make sure clashfarmer is open and visible on screen.")

        time.sleep(30)

if __name__ == "__main__":
    main()
