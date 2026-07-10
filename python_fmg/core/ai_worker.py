import sys
import json
import urllib.request
import sqlite3
from PyQt6.QtCore import QThread, pyqtSignal

class CommandInterceptor:
    """
    Parses command text patterns from chat inputs, directly updating SQLite 
    or modifying map parameters before feeding queries to LLMs.
    """
    @staticmethod
    def intercept_and_execute(user_input, db_path):
        if not user_input.startswith("/"):
            return None
            
        parts = user_input.strip().split()
        cmd = parts[0].lower()
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # /war [faction1_id] [faction2_id]
            if cmd == "/war" and len(parts) >= 3:
                f1, f2 = int(parts[1]), int(parts[2])
                cursor.execute("""
                    INSERT INTO inconsistencies (source_type, description, status)
                    VALUES (?, ?, ?)
                """, ("War Declared", f"State {f1} has declared war against State {f2}!", "Active"))
                conn.commit()
                conn.close()
                return f"[System Command] State {f1} declared war against State {f2}. Geopolitical parameters updated."
                
            # /place_burg [name] [cell_idx]
            elif cmd == "/place_burg" and len(parts) >= 3:
                name = parts[1]
                cell_idx = int(parts[2])
                cursor.execute("""
                    INSERT INTO settlements (name, q, r, population, faction_id)
                    VALUES (?, ?, 0, 5000, 1)
                """, (name, cell_idx))
                conn.commit()
                conn.close()
                return f"[System Command] Burg '{name}' procedurally placed at Cell Index {cell_idx}."
                
            # /settle [cell_idx] [state_id]
            elif cmd == "/settle" and len(parts) >= 3:
                cell_idx = int(parts[1])
                state_id = int(parts[2])
                cursor.execute("UPDATE cells SET state_id=? WHERE id=?", (state_id, cell_idx))
                conn.commit()
                conn.close()
                return f"[System Command] Border claimed: Cell {cell_idx} is now assigned to State {state_id}."
                
            conn.close()
        except Exception as e:
            return f"[System Command Error] Command execution failed: {e}"
            
        return "[System Command Error] Unknown or malformed command pattern."

class OllamaPromptWorker(QThread):
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, prompt, db_path="lore_forge_world.db", system_instruction=None, model="qwen2.5:latest", genre="Fantasy"):
        super().__init__()
        self.prompt = prompt
        self.db_path = db_path
        self.model = model
        self.genre = genre
        
        # Check for client text commands first before feeding to LLM
        intercepted_response = CommandInterceptor.intercept_and_execute(prompt, db_path)
        self.intercepted_text = intercepted_response
        
        world_context = self.load_database_context()
        templates_context = self.load_templates_context()

        self.system_instruction = system_instruction or (
            "You are Worldsmith AI, an analytical assistant guiding a TTRPG worldbuilder. "
            "You do NOT write creative content, prose, or generate names. All creative writing must be done by the user. "
            "Your role is to organize their thoughts, audit their lore for contradictions, "
            "and actively interview the user via the chat panel with open-ended questions to encourage them to flesh out missing details.\n\n"
            "When the user is defining a new entity (like a Species, Culture, or Faction), look at the 'Active Templates' list. "
            "Prompt them to provide the specific subheadings required by that template category. Do not invent the answers; ask them probing questions to help them fill it out.\n\n"
            f"You must strictly adhere to the {self.genre} genre. Flag any out-of-genre elements the user writes.\n\n"
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
        # Short-circuit thread if command was intercepted and executed locally
        if self.intercepted_text:
            self.response_received.emit(self.intercepted_text)
            return
            
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

    def __init__(self, note_title, note_content, db_path="lore_forge_world.db", model="qwen2.5:latest", genre="Fantasy"):
        super().__init__()
        self.note_title = note_title
        self.note_content = note_content
        self.db_path = db_path
        self.model = model
        self.genre = genre

    def run(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT c.elevation, c.biome, c.state_id, m.magic_type 
                FROM note_map_bindings b
                JOIN cells c ON b.cell_idx = c.id
                LEFT JOIN magic_layers m ON c.id = m.cell_idx
                JOIN notes n ON b.note_id = n.id
                WHERE n.title = ?
            """, (self.note_title,))
            geo_context = cursor.fetchone()
            conn.close()

            system_prompt = (
                "You are a strict TTRPG worldbuilding validator. Your job is to find structural "
                "contradictions between user written text and established map data.\n\n"
                "CRITICAL RULES:\n"
                f"- The setting is strictly {self.genre}. Flag any out-of-genre elements as inconsistencies.\n"
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

class LorePromptWorker(QThread):
    prompt_ready = pyqtSignal(str)
    
    def __init__(self, context_data, db_path="lore_forge_world.db", model="qwen2.5:latest", genre="Fantasy"):
        super().__init__()
        self.context_data = context_data
        self.db_path = db_path
        self.model = model
        self.genre = genre
        
    def run(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            entity_name = self.context_data.get('name', '')
            if not entity_name:
                conn.close()
                return
                
            cursor.execute("SELECT count(*) FROM notes WHERE title LIKE ? OR content LIKE ?", (f"%{entity_name}%", f"%{entity_name}%"))
            note_count = cursor.fetchone()[0]
            conn.close()
            
            if note_count > 0:
                # Lore already exists, no need to push a prompt
                return
                
            system_prompt = (
                f"You are an active worldbuilding auditor operating strictly within a {self.genre} setting. "
                "The user just selected a location or faction on the map that has NO recorded lore. "
                "Ask a single, intriguing, creative question to prompt the user to invent some lore for it themselves. "
                "Keep it under 2 sentences. Be specific using the provided details. "
                "CRITICAL: Do NOT answer the question yourself, do NOT invent names, and do NOT write creative content."
            )
            
            user_prompt = f"Entity Name: {entity_name}\nType: {self.context_data.get('type')}\nDetails: {self.context_data}"
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
                if result:
                    # Prepend a special token so the chat UI knows this is an active prompt
                    self.prompt_ready.emit(f"[ACTIVE_PROMPT] {entity_name}: {result}")
        except Exception as e:
            print(f"LorePromptWorker error: {e}")

import os
import time
from python_fmg.core.template_manager import TemplateManager

class AILoreIngestor(QThread):
    progress_update = pyqtSignal(int, int, str) # current, total, filename
    ingestion_complete = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, file_queue, db_path, lore_dir, model="qwen2.5:latest", genre="Fantasy"):
        super().__init__()
        self.file_queue = file_queue
        self.db_path = db_path
        self.lore_dir = lore_dir
        self.model = model
        self.genre = genre
        self.template_mgr = TemplateManager(self.db_path)
        self.templates = self.template_mgr.get_all_templates()
        
    def run(self):
        total = len(self.file_queue)
        for idx, file_path in enumerate(self.file_queue):
            filename = os.path.basename(file_path)
            self.progress_update.emit(idx + 1, total, filename)
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # Ask AI to categorize and format
                categories = list(self.templates.keys())
                system_prompt = (
                    "You are a strict data ingestion parser for a worldbuilding application.\n"
                    "The user will provide raw text.\n"
                    "Step 1: Determine which of the following categories this text best fits into: " + ", ".join(categories) + ".\n"
                    "Step 2: Format the text using the exact subheadings required by that category. "
                    "If the text lacks information for a subheading, output EXACTLY the tag '[NEEDS_DETAIL]' under that subheading.\n"
                    "Output format must be JSON:\n"
                    "{\"category\": \"CategoryName\", \"content\": \"# Title\\n\\n## Subheading 1\\nContent\\n\\n## Subheading 2\\n[NEEDS_DETAIL]\"}\n"
                    "Do not output any markdown code blocks outside the JSON. Return only the JSON object."
                )
                
                full_prompt = f"System: {system_prompt}\n\nUser: {content}"
                data = json.dumps({
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "format": "json"
                }).encode("utf-8")
                
                req = urllib.request.Request(
                    "http://localhost:11434/api/generate",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                
                with urllib.request.urlopen(req, timeout=120) as response:
                    resp_data = json.loads(response.read().decode("utf-8"))
                    result_json = json.loads(resp_data.get("response", "{}"))
                    
                    category = result_json.get("category", "Meta")
                    formatted_content = result_json.get("content", content)
                    
                    if category not in categories:
                        category = "Meta"
                        
                    # Save to the categorized folder
                    cat_dir = os.path.join(self.lore_dir, category)
                    os.makedirs(cat_dir, exist_ok=True)
                    dest_path = os.path.join(cat_dir, filename)
                    
                    with open(dest_path, "w", encoding="utf-8") as out_f:
                        out_f.write(formatted_content)
                        
            except Exception as e:
                print(f"Error ingesting {filename}: {e}")
                self.error_occurred.emit(str(e))
                
        self.ingestion_complete.emit()

class AILoreDriverWorker(QThread):
    prompt_ready = pyqtSignal(str, str, str) # title, subheading, prompt_text
    
    def __init__(self, lore_dir, model="qwen2.5:latest", genre="Fantasy"):
        super().__init__()
        self.lore_dir = lore_dir
        self.model = model
        self.genre = genre
        
    def run(self):
        try:
            target_file = None
            target_subheading = None
            
            for root, dirs, files in os.walk(self.lore_dir):
                for f in files:
                    if f.endswith('.md'):
                        path = os.path.join(root, f)
                        with open(path, 'r', encoding='utf-8') as file:
                            lines = file.readlines()
                            current_subheading = None
                            for line in lines:
                                if line.startswith('## '):
                                    current_subheading = line.strip()[3:]
                                elif '[NEEDS_DETAIL]' in line or '[CONFLICT]' in line:
                                    target_file = path
                                    target_subheading = current_subheading
                                    break
                        if target_file:
                            break
                if target_file:
                    break
                    
            if not target_file:
                return # No gaps found
                
            filename = os.path.basename(target_file)
            title = os.path.splitext(filename)[0]
            
            system_prompt = (
                f"You are Worldsmith AI, an active worldbuilding director in a {self.genre} setting.\n"
                f"The user has a note titled '{title}' that is missing information under the subheading '{target_subheading}'.\n"
                "Ask exactly ONE short, probing question to encourage the user to fill out this specific missing detail.\n"
                "CRITICAL: Do NOT answer the question yourself. Do not write creative content. Ask only the question."
            )
            
            data = json.dumps({
                "model": self.model,
                "prompt": f"System: {system_prompt}\n\nUser: I need to fill out {target_subheading} for {title}. Ask me a question about it.",
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
                if result:
                    self.prompt_ready.emit(target_file, target_subheading, result)
        except Exception as e:
            print(f"AILoreDriverWorker error: {e}")
