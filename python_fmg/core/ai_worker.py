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
        
        world_context = self.load_database_context()
        templates_context = self.load_templates_context()

        # Upgraded system directive to enforce a proactive, conversational interview loop
        self.system_instruction = system_instruction or (
            "You are Worldsmith AI, an interactive co-author guiding a TTRPG worldbuilder. "
            "Do not just passively respond. You must actively interview the user via the chat panel, "
            "prompting them with clear, open-ended questions to flesh out missing details, "
            "explore historical gaps, and resolve any contradictions between their text and map geography. "
            "If the user makes a statement that fills in one of the templates, explicitly state how you "
            "are updating that template.\n\n"
            f"Active Templates to enforce:\n{templates_context}\n\n"
            f"Active World Context:\n{world_context}"
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

class LoreAuditWorker(QThread):
    audit_completed = pyqtSignal(str)

    def __init__(self, note_title, note_content, db_path="lore_forge_world.db", model="qwen2.5:latest"):
        super().__init__()
        self.note_title = note_title
        self.note_content = note_content
        self.db_path = db_path
        self.model = model

    def run(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT c.elevation, c.biome, c.state_id, m.magic_type 
                FROM note_map_bindings b
                JOIN cells c ON b.cell_idx = c.id
                LEFT JOIN magic_layer m ON c.id = m.cell_id
                JOIN notes n ON b.note_id = n.id
                WHERE n.title = ?
            """, (self.note_title,))
            geo_context = cursor.fetchone()
            conn.close()

            system_prompt = (
                "You are a strict TTRPG worldbuilding validator. Your job is to find structural "
                "contradictions between user written text and established map data.\n\n"
                "CRITICAL RULES:\n"
                "- If the text contradicts the geography, log an inconsistency.\n"
                "- If there are no inconsistencies, reply with only the word 'None'."
            )
            
            user_prompt = f"Note Title: {self.note_title}\nContent: {self.note_content}\n"
            if geo_context:
                user_prompt += f"Map Context: Elevation={geo_context[0]}, Biome={geo_context[1]}, Controller State ID={geo_context[2]}, Magic Pollution={geo_context[3]}"
            
            full_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"
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
                result = resp_data.get("response", "").strip()
                
                if result.lower() != "none" and len(result) > 5:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO inconsistencies (source_type, description, status)
                        VALUES (?, ?, ?)
                    """, ("Note Map Conflict", f"Note '{self.note_title}': {result}", "Active"))
                    conn.commit()
                    conn.close()
                    
                    self.audit_completed.emit(result)
                else:
                    self.audit_completed.emit("")
        except Exception as e:
            self.audit_completed.emit("")
