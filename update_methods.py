import os

filepath = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """    def handle_wiki_link_clicked(self, title):
        try:
            conn = sqlite3.connect(self.db_path, timeout=15.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM notes WHERE title = ?", (title,))
            res = cursor.fetchone()
            conn.close()
            if res:
                self.note_writer.setText(res[0])
            else:
                QMessageBox.information(self, "Note Not Found", f"No lore entry found for: {title}")
        except Exception as e:
            print(f"Error fetching note: {e}")"""

new_block = """    def handle_wiki_link_clicked(self, title):
        try:
            conn = sqlite3.connect(self.db_path, timeout=15.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM notes WHERE title = ?", (title,))
            res = cursor.fetchone()
            conn.close()
            if res:
                self.note_writer.setText(res[0])
            else:
                QMessageBox.information(self, "Note Not Found", f"No lore entry found for: {title}")
        except Exception as e:
            print(f"Error fetching note: {e}")

    def handle_vault_item_clicked(self, index):
        if not self.vault_model.isDir(index):
            file_path = self.vault_model.filePath(index)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.note_writer.setText(content)
                self.left_tabs.setCurrentIndex(0) # switch to editor tab
            except Exception as e:
                QMessageBox.critical(self, "Error reading file", str(e))

    def handle_ai_submit(self):
        user_text = self.ai_input.text().strip()
        if not user_text:
            return
            
        self.ai_input.clear()
        
        self.ai_prompt_history.append(
            f'<div style="text-align: right; margin: 2px 4px 6px 30px;">'
            f'<span style="background-color: #3b82f6; color: white; padding: 4px 8px; border-radius: 6px; display: inline-block;">'
            f'<b>You:</b> {user_text}</span></div>'
        )
        
        system_instr = "You are Lordsmith AI, a master cartographer and chronicler of Fantasy worlds. You help users expand their worldbuilding notes and answer questions about their generated content."
        
        genre = "Fantasy"
        self.ai_worker = OllamaPromptWorker(user_text, db_path=self.db_path, genre=genre)
        self.ai_worker.response_received.connect(self.handle_ai_response)
        self.ai_worker.start()

    def handle_ai_response(self, text):
        self.ai_prompt_history.append(
            f'<div style="text-align: left; margin: 2px 30px 6px 4px;">'
            f'<span style="background-color: #29293a; color: #EEEEF8; padding: 4px 8px; border-radius: 6px; display: inline-block;">'
            f'<span style="color: #04D361; font-weight: bold;">AI:</span> {text}</span></div>'
        )"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Methods Updated')
else:
    print('Could not find methods block')
