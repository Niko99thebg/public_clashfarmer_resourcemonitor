#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import glob
import stat

def on_rm_error(func, path, exc_info):
    """
    Callback per shutil.rmtree: rimuove il flag di sola lettura e riprova.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)

def build_exe():
    """
    Genera un exe standalone di BuilderHallBot includendo
    automaticamente tutte le immagini .png e le icone .ico presenti nella
    cartella corrente e poi pulisce manualmente le cartelle di build.
    """
    script_name = "main.py"
    exe_name    = "ClashFarmerMonitor"

    print(f"=== Building {exe_name}.exe ===\n")

    python_exe = sys.executable

    # Costruiamo il comando PyInstaller SENZA --clean per evitare errori interni
    command = [
        python_exe, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--icon=icon.ico",
        "--name", exe_name,
        script_name
    ]

    # Aggiungi automaticamente tutte le risorse .png e .ico
    for pattern in ("*.png", "*.ico"):
        for fn in glob.glob(pattern):
            if fn == script_name:
                continue
            src = os.path.abspath(fn)
            command += ["--add-data", f"{src};."]

    try:
        subprocess.run(command, check=True)
        print(f"\n✅ Build complete! Troverai {exe_name}.exe in dist/")
    except subprocess.CalledProcessError as e:
        print("\n❌ Build failed!")
        print(e)
        sys.exit(1)

    # Pulizia manuale
    print("\n🧹 Cleaning up temporary files...")
    for folder in ("build", "__pycache__"):
        if os.path.isdir(folder):
            try:
                shutil.rmtree(folder, onerror=on_rm_error)
                print(f"Deleted folder: {folder}")
            except Exception as e:
                print(f"Warning: non ho potuto cancellare '{folder}': {e}")

    spec_file = f"{exe_name}.spec"
    if os.path.exists(spec_file):
        try:
            os.remove(spec_file)
            print(f"Deleted file: {spec_file}")
        except Exception as e:
            print(f"Warning: non ho potuto cancellare '{spec_file}': {e}")

    print("✅ Cleanup complete.\n")

if __name__ == "__main__":
    build_exe()
