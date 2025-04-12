import os
import subprocess
import shutil
import sys

def build_exe():
    print("=== Building ClashFarmerMonitor.exe ===\n")

    command = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--icon=icon.ico",
        "--add-data=exit_icon.png;.",
        "--add-data=start_icon.png;.",
        "--add-data=stop_icon.png;.",
        "--add-data=refresh_icon.png;.",
        "--add-data=save_icon.png;.",
        "--name=ClashFarmerMonitor",
        "main.py"
    ]

    try:
        subprocess.run(command, check=True)
        print("\n✅ Build complete! Check the 'dist' folder for ClashFarmerMonitor.exe")
    except subprocess.CalledProcessError as e:
        print("\n❌ Build failed!")
        print(e)
        sys.exit(1)

    # Cleanup temporary files
    print("\n🧹 Cleaning up temporary files...")

    for folder in ["build", "__pycache__"]:
        if os.path.isdir(folder):
            shutil.rmtree(folder)
            print(f"Deleted folder: {folder}")

    spec_file = "ClashFarmerMonitor.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"Deleted file: {spec_file}")

    print("✅ Cleanup complete.")

if __name__ == "__main__":
    build_exe()
