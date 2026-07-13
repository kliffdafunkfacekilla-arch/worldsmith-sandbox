import os

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_block = """    def on_ingestion_complete(self):
        self.progress_dialog.setValue(self.progress_dialog.maximum())
        QMessageBox.information(self, "Success", "Lore successfully ingested and synchronized with SQLite database!")"""
        
    new_block = """    def on_ingestion_complete(self, is_online):
        self.progress_dialog.setValue(self.progress_dialog.maximum())
        if is_online:
            QMessageBox.information(self, "Success", "Lore successfully ingested and synchronized with SQLite database!")
        else:
            QMessageBox.warning(self, "Offline Mode", "Lore was saved as plain text, but AI Entity Extraction failed! No Ollama instance was found on port 11434 and no Gemini API key was provided.")"""
            
    if old_block in content:
        content = content.replace(old_block, new_block)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Fixed {filepath}')
    else:
        print(f'Could not find block in {filepath}')

fix_file(r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\main.py')
fix_file(r'c:\Users\krazy\Desktop\worldsmith-sandbox\main_import.py')
