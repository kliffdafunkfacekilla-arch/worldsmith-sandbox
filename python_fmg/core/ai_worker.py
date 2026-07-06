import sys
import json
import urllib.request
import sqlite3
from PyQt6.QtCore import QThread, pyqtSignal

class OllamaPromptWorker(QThread):
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, prompt, db_path="lore_forge_world.db", system_instruction=None, model="qwen2.5:latest"):
        super().__init__()
        self.prompt = prompt
        self.db_path = db_path
        self.model = model
        
        # Load active database context & custom templates for prompt injection
        world_context = self.load_database_context()
        templates_context = self.load_templates_context()

        self.system_instruction = system_instruction or (
            "You are Worldsmith AI, an interactive co-author helping the user build a custom world. "
            "Prompt the user with clear, open questions to fill in missing details. "
            "Adhere strictly to the custom templates and categories defined by the user. "
            f"Here are the active custom templates to fill in:\n{templates_context}\n\n"
            f"Here is the active world data context:\n{world_context}"
        )

    def load_templates_context(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT category, fields_json FROM world_templates")
            rows = cursor.fetchall()
            conn.close()
            
            output = []
            for row in rows:
                fields = json.loads(row[1])
                output.append(f"- Category '{row[0]}': requires fields: {', '.join(fields)}")
            return "\n".join(output)
        except:
            return "No custom templates loaded."

    def load_database_context(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT title FROM notes LIMIT 10")
            notes = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("SELECT name FROM factions LIMIT 5")
            factions = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("SELECT COUNT(*) FROM settlements")
            settlements_count = cursor.fetchone()[0]
            
            conn.close()
            return f"- Notes Index: {notes}\n- Factions Index: {factions}\n- Settlement count: {settlements_count}"
        except:
            return "No active database context loaded."

    def run(self):
        try:
            full_prompt = f"System: {self.system_instruction}\n\nUser: {self.prompt}"
            data = json.dumps({
                "model": self.model,
                "prompt": full_prompt,
                "stream": False
            }).encode("utf-8")

            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                resp_data = json.loads(response.read().decode("utf-8"))
                text = resp_data.get("response", "").strip()
                self.response_received.emit(text)

        except Exception as e:
            self.error_occurred.emit(str(e))
