#!/usr/bin/env python3
"""
chatgpt_automation.py

A PyQt5 GUI for automating interactions with ChatGPT in a browser via undetected_chromedriver.
Features:
  - Drag & drop .py files or entire folders into the GUI.
  - Batch prompt processing: process multiple files sequentially.
  - Auto-code deployment: after processing, run tests and deploy refactored code automatically.
  - Automatically handle "Continue generating" clicks.
  - Copy ChatGPT's response to the clipboard.
  - Save the response as a new file (appending "_refactored.py" to the original filename).
  - (Optional) Auto-paste response into an editor.

Before running:
  1. Ensure you have ChromeDriver installed and set in CHROMEDRIVER_PATH.
  2. Run the script once with save_cookies() (uncomment it) to log in manually and save cookies.
  3. For subsequent runs, comment out save_cookies().

Usage:
    python chatgpt_automation.py
"""

import sys
import time
import json
import os
import shutil
from pathlib import Path

import pyperclip
import pyautogui

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QCloseEvent

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# ---------- Import OpenAI Login Module ----------
from openai_login import get_openai_driver, login_openai

# ---------- CONFIGURATION ----------
CHATGPT_URL = "https://chat.openai.com/"
COOKIE_FILE = "chatgpt_cookies.json"
CHROMEDRIVER_PATH = r"C:/Users/USER/Downloads/chromedriver-win64/chromedriver.exe"  # Use absolute path
HEADLESS = False  # We want a visible browser

# We'll define a full absolute path for the Chrome profile:
CURRENT_DIR = os.path.abspath(os.getcwd())
PROFILE_DIR = os.path.join(CURRENT_DIR, "chrome_profile", "openai")
os.makedirs(PROFILE_DIR, exist_ok=True)  # Ensure directory is created

# ---------- Initialize the Selenium driver with user-data-dir ----------
driver = get_openai_driver(profile_path=PROFILE_DIR, headless=HEADLESS)
if not login_openai(driver):
    print("OpenAI Login Failed. Exiting.")
    sys.exit(1)

# ---------- BATCH & DEPLOY CONFIGURATION ----------
DEPLOY_FOLDER = Path("deployed")
DEPLOY_FOLDER.mkdir(exist_ok=True)
BACKUP_FOLDER = Path("backups")
BACKUP_FOLDER.mkdir(exist_ok=True)

def send_prompt(prompt: str) -> str:
    """Send a prompt to ChatGPT and return the full response."""
    print("Sending prompt...")
    try:
        textarea = driver.find_element(By.TAG_NAME, "textarea")
    except Exception as e:
        print(f"Error locating textarea: {e}")
        return ""
    textarea.clear()
    textarea.send_keys(prompt)
    textarea.send_keys(Keys.ENTER)
    time.sleep(5)  # Wait for initial response
    return get_full_response()

def get_full_response(timeout: int = 120) -> str:
    """
    Waits for ChatGPT's complete response, handling "Continue generating" clicks.
    Breaks out after 'timeout' seconds if no stable response is received.
    """
    print("Waiting for full response...")
    start_time = time.time()
    full_response = ""
    last_response = ""
    while True:
        if time.time() - start_time > timeout:
            print("Timeout reached while waiting for response.")
            break
        time.sleep(3)
        try:
            messages = driver.find_elements(By.CSS_SELECTOR, ".markdown.prose.w-full.break-words")
        except Exception as e:
            print(f"Error retrieving messages: {e}")
            messages = []
        if messages:
            last_response = messages[-1].text
            print("Response update: length =", len(last_response))
        else:
            print("No response yet.")
        # Handle "Continue generating" button if present
        try:
            continue_button = driver.find_element(By.XPATH, "//button[contains(., 'Continue generating')]")
            if continue_button.is_displayed():
                print("Clicking 'Continue generating'...")
                continue_button.click()
                time.sleep(5)
                continue
        except Exception:
            pass
        # Check if response stabilized
        if last_response == full_response and last_response != "":
            print("Response complete.")
            break
        full_response = last_response
    return full_response

def copy_to_clipboard(content: str) -> None:
    """Copy the provided content to the system clipboard."""
    pyperclip.copy(content)
    print("Response copied to clipboard.")

def paste_into_editor(hotkey_sequence: str = "ctrl+v", delay_before_paste: int = 2) -> None:
    """
    Auto-pastes clipboard content into an active editor using the specified hotkey sequence.
    Adjust hotkey_sequence for your OS (e.g., "command+v" on macOS).
    """
    print(f"Waiting {delay_before_paste} seconds before pasting into editor...")
    time.sleep(delay_before_paste)
    pyautogui.hotkey(*hotkey_sequence.split('+'))
    print("Pasted into editor.")

def run_tests(file_path: str) -> bool:
    """
    Dummy test function: verifies file exists and is not empty.
    Replace this with your actual test suite logic.
    """
    try:
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            print("Tests passed.")
            return True
    except Exception as e:
        print(f"Test error: {e}")
    return False

def deploy_file(file_path: str) -> None:
    """
    Deploys the file by moving it to the DEPLOY_FOLDER and saving a backup in BACKUP_FOLDER.
    """
    backup_path = BACKUP_FOLDER / (Path(file_path).stem + "_backup.py")
    deploy_path = DEPLOY_FOLDER / Path(file_path).name
    try:
        shutil.copy2(file_path, backup_path)
        shutil.move(file_path, deploy_path)
        print(f"Deployed file to {deploy_path}. Backup saved at {backup_path}.")
    except Exception as e:
        print(f"Deployment error: {e}")

def process_file(file_path: str) -> None:
    """
    Processes a file by reading its content, sending it as a prompt to ChatGPT,
    saving the AI-refactored code as a new file, copying the response to clipboard,
    and then running tests and deploying if tests pass.
    """
    print(f"Processing file: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            file_content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return

    prompt = "Refactor this code for general use:\n\n" + file_content
    response = send_prompt(prompt)
    if not response:
        print("No response received.")
        return
    output_file = file_path.replace(".py", "_refactored.py")
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(response)
        print(f"Refactored file saved to: {output_file}")
    except Exception as e:
        print(f"Error writing to {output_file}: {e}")
    copy_to_clipboard(response)
    if run_tests(output_file):
        deploy_file(output_file)
    else:
        print("Tests failed. Deployment aborted.")

# ---------- PyQt5 GUI Components ----------
class Worker(QtCore.QThread):
    result_signal = QtCore.pyqtSignal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self) -> None:
        try:
            process_file(self.file_path)
            self.result_signal.emit(f"Processed: {self.file_path}")
        except Exception as e:
            self.result_signal.emit(f"Error processing {self.file_path}: {e}")

class ChatGPTAutomationGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatGPT Automation")
        self.setGeometry(100, 100, 800, 600)
        self.init_ui()
        self.workers = []

    def init_ui(self) -> None:
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        self.file_list = QtWidgets.QListWidget()
        self.file_list.setAcceptDrops(True)
        # We remove type hints for dragEnterEvent and dropEvent
        self.file_list.dragEnterEvent = self.dragEnterEvent
        self.file_list.dropEvent = self.dropEvent
        layout.addWidget(self.file_list)

        self.start_button = QtWidgets.QPushButton("Start Processing")
        self.start_button.clicked.connect(self.start_processing)
        layout.addWidget(self.start_button)

        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            # If it's a folder, add all .py files inside it
            if os.path.isdir(file_path):
                for root, _, files in os.walk(file_path):
                    for file in files:
                        if file.endswith(".py"):
                            full_path = os.path.join(root, file)
                            self.file_list.addItem(full_path)
            else:
                if file_path.endswith(".py"):
                    self.file_list.addItem(file_path)

    def log(self, message: str) -> None:
        self.log_text.appendPlainText(message)

    def start_processing(self) -> None:
        self.log("Starting processing of files...")
        for index in range(self.file_list.count()):
            file_path = self.file_list.item(index).text()
            worker = Worker(file_path)
            worker.result_signal.connect(self.log)
            worker.start()
            self.workers.append(worker)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Ensure the Selenium driver is closed when the GUI is closed."""
        try:
            driver.quit()
            self.log("Selenium driver closed.")
        except Exception as e:
            self.log(f"Error closing Selenium driver: {e}")
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    gui = ChatGPTAutomationGUI()
    gui.show()
    sys.exit(app.exec_())
