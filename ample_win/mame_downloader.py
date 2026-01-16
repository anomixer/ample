import os
import requests
import subprocess
from PySide6.QtCore import QThread, Signal

class MameDownloadWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(bool, str)
    status = Signal(str)

    def __init__(self, dest_dir):
        super().__init__()
        self.dest_dir = dest_dir
        # MAME official self-extracting EXE - Updated to 0.284
        self.url = "https://github.com/mamedev/mame/releases/download/mame0284/mame0284b_x64.exe"

    def run(self):
        try:
            self.status.emit("Downloading MAME installer...")
            response = requests.get(self.url, stream=True, timeout=60, allow_redirects=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            # Use official filename from URL
            filename = self.url.split('/')[-1]
            exe_path = os.path.join(self.dest_dir, filename)
            os.makedirs(self.dest_dir, exist_ok=True)
            
            downloaded = 0
            with open(exe_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total_size)
            
            self.status.emit("Opening installer...")
            # Use os.startfile to run the self-extractor on Windows
            os.startfile(exe_path)
            self.finished.emit(True, exe_path)
                
        except Exception as e:
            self.status.emit(f"Error: {str(e)}")
            self.finished.emit(False, str(e))
