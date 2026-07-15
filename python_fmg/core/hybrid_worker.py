import sys
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal

class HybridPipelineWorker(QThread):
    progress_update = pyqtSignal(int, int, str)
    ingestion_complete = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        import os
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "ingest_lore.py"))
        
        # Determine total files approximately
        vault_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "lore_vault"))
        total = 0
        for root, _, files in os.walk(vault_dir):
            for file in files:
                if file.endswith('.md'):
                    total += 1
                    
        if total == 0:
            total = 1 # avoid div zero
            
        cur = 0
        try:
            process = subprocess.Popen([sys.executable, script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in process.stdout:
                line = line.strip()
                if line.startswith("Processing"):
                    cur += 1
                    self.progress_update.emit(cur, total, line.split()[1])
                elif line.startswith("Skipping"):
                    cur += 1
                    self.progress_update.emit(cur, total, line)
            
            process.wait()
            self.ingestion_complete.emit(process.returncode == 0)
        except Exception as e:
            print("Error running script:", e)
            self.ingestion_complete.emit(False)
