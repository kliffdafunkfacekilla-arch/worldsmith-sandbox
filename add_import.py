import os

file_path = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\main.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add the action to the menu
menu_code = '''        action_export_wiki = file_menu.addAction("Export Static HTML Wiki")
        action_export_wiki.triggered.connect(self.action_export_wiki)
'''
new_menu_code = menu_code + '''
        action_import_lore = file_menu.addAction("📥 Import Markdown Vault (.md)")
        action_import_lore.triggered.connect(self.action_import_lore)
'''
content = content.replace(menu_code, new_menu_code)

# Add the handler function to LordsmithStudioMainWindow
handler_code = '''
    def action_import_lore(self):
        from PyQt6.QtWidgets import QFileDialog, QProgressDialog
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Markdown Lore Files", "", "Markdown Files (*.md);;All Files (*)")
        if not file_paths:
            return
            
        vault_dir = os.path.join(self.project_dir, 'lore_vault')
        self.ingestor = AILoreIngestor(file_paths, self.db_path, vault_dir, parent=self)
        
        self.progress_dialog = QProgressDialog("Ingesting Lore and Extracting Entities...", "Cancel", 0, len(file_paths), self)
        self.progress_dialog.setWindowTitle("AI Ingestion Engine")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setStyleSheet("background-color: #0c0c10; color: #fff;")
        
        self.ingestor.progress_update.connect(lambda cur, tot, name: self.progress_dialog.setValue(cur))
        self.ingestor.progress_update.connect(lambda cur, tot, name: self.progress_dialog.setLabelText(f"Parsing: {name}"))
        self.ingestor.ingestion_complete.connect(self.on_ingestion_complete)
        
        self.progress_dialog.show()
        self.ingestor.start()

    def on_ingestion_complete(self, is_online):
        self.progress_dialog.setValue(self.progress_dialog.maximum())
        if is_online:
            QMessageBox.information(self, "Success", "Lore successfully ingested and synchronized with SQLite database!")
        else:
            QMessageBox.warning(self, "Offline Mode", "Lore was saved as plain text, but AI Entity Extraction failed! No Ollama instance was found on port 11434 and no Gemini API key was provided.")
        self.w_factions.refresh_grid()
        self.w_provinces.refresh_grid()
        # Trigger map canvas re-render since new cities might have spawned
        self.map_viewer_canvas.update()
'''

class_end_search = '    def action_export_wiki(self):'
content = content.replace(class_end_search, handler_code + '\n' + class_end_search)

with open('main_import.py', 'w', encoding='utf-8') as f:
    f.write(content)
