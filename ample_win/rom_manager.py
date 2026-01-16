import os
import requests
import plistlib
from PySide6.QtCore import QObject, Signal, QThread

class DownloadWorker(QThread):
    progress = Signal(int, int) # current, total
    finished = Signal(str, bool) # value, success
    status = Signal(str)

    def __init__(self, url, dest_path, value):
        super().__init__()
        self.url = url
        self.dest_path = dest_path
        self.value = value

    def run(self):
        try:
            response = requests.get(self.url, stream=True, timeout=30)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            os.makedirs(os.path.dirname(self.dest_path), exist_ok=True)
            
            downloaded = 0
            with open(self.dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.isInterruptionRequested():
                        self.status.emit("Download cancelled.")
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            self.progress.emit(downloaded, total_size)
            
            self.finished.emit(self.value, True)
        except Exception as e:
            if os.path.exists(self.dest_path):
                try: os.remove(self.dest_path)
                except: pass
            self.status.emit(f"Error: {str(e)}")
            self.finished.emit(self.value, False)

class RomManager(QObject):
    def __init__(self, resources_path, roms_dir):
        super().__init__()
        self.resources_path = resources_path
        self.roms_dir = roms_dir
        self.base_url = "https://www.callapple.org/roms/"
        self.rom_list = self.load_rom_list()

    def load_rom_list(self):
        path = os.path.join(self.resources_path, "roms.plist")
        if not os.path.exists(path):
            return []
        with open(path, 'rb') as f:
            return plistlib.load(f)

    def get_rom_status(self):
        status_list = []
        for rom in self.rom_list:
            value = rom['value']
            # Check for zip or 7z
            found = False
            for ext in ['zip', '7z']:
                path = os.path.join(self.roms_dir, f"{value}.{ext}")
                if os.path.exists(path):
                    found = True
                    break
            
            status_list.append({
                'value': value,
                'description': rom['description'],
                'exists': found
            })
        return status_list

    def get_download_url(self, value, ext='zip'):
        return f"{self.base_url}{value}.{ext}"
