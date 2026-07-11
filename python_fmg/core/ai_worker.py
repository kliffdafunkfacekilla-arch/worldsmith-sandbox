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

    def process_lore_compliance_checks(self, note_title, note_body, frontmatter_dict, disabled_layers):
        """
        Evaluates cross-layer data logic. Aborts inference loop if inline 
        comments or frontmatter dictionaries contain explicit 'ai-ignore' command tags.
        """
        # Check for direct Frontmatter override instructions
        ai_overrides = frontmatter_dict.get("ai_override", [])
        
        # Check for inline user escape strings inside note content body
        if "<!-- ai-ignore hydrology_uphill -->" in note_body:
            ai_overrides.append("hydrology_uphill")
        if "<!-- ai-ignore crime_proximity -->" in note_body:
            ai_overrides.append("crime_proximity")

        detected_anomalies = []

        # Validation Rule A: River direction compliance check
        if "hydrology_uphill" not in ai_overrides and "Rivers" not in disabled_layers:
            pass

        # Validation Rule B: Smuggling and Crime Layer strategic compliance check
        if "crime_proximity" not in ai_overrides and "Underworld & Crime" not in disabled_layers:
            if frontmatter_dict.get("security_rating") == "Absolute" and frontmatter_dict.get("layer_z", "surface") == "surface":
                detected_anomalies.append("Conflict: High security notation overlaps an active syndicate territory zone.")

        return detected_anomalies

    def run(self):
        try:
            # Parse simple frontmatter if it exists
            frontmatter_dict = {}
            if self.note_content.startswith("---"):
                parts = self.note_content.split("---", 2)
                if len(parts) >= 3:
                    import yaml
                    try:
                        frontmatter_dict = yaml.safe_load(parts[1]) or {}
                    except:
                        pass
            
            anomalies = self.process_lore_compliance_checks(self.note_title, self.note_content, frontmatter_dict, [])
            if anomalies:
                self.audit_completed.emit("Anomaly detected before inference:\n" + "\n".join(anomalies))
                return

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
                    "The user will provide a long raw text document that contains MULTIPLE distinct topics or chapters.\n"
                    "Step 1: Slice the text into distinct, separate topics or entities.\n"
                    "Step 2: For EACH topic, determine which of the following EXACT categories it best fits into: " + ", ".join(f"'{c}'" for c in categories) + ".\n"
                    "You MUST use EXACTLY one of the strings provided above for the 'category' field.\n"
                    "Step 3: Format each topic using the exact subheadings required by that category. "
                    "If the topic lacks information for a subheading, output EXACTLY the tag '[NEEDS_DETAIL]' under that subheading.\n"
                    "Output format must be a JSON ARRAY of objects:\n"
                    "[\n"
                    "  {\"title\": \"Safe_Filename_Title\", \"category\": \"ExactCategoryName\", \"content\": \"# Title\\n\\n## Subheading 1\\nContent\\n\\n## Subheading 2\\n[NEEDS_DETAIL]\"},\n"
                    "  {\"title\": \"Another_Topic\", \"category\": \"ExactCategoryName\", \"content\": \"...\"}\n"
                    "]\n"
                    "Do not output any markdown code blocks outside the JSON array. Return only the JSON array."
                )
                
                full_prompt = f"System: {system_prompt}\n\nUser: {content}"
                
                import urllib.request
                import json
                
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
                
                with urllib.request.urlopen(req, timeout=600) as response:
                    resp_data = json.loads(response.read().decode("utf-8"))
                    raw_response = resp_data.get("response", "[]").strip()
                    
                    if raw_response.startswith("```json"):
                        raw_response = raw_response[7:]
                    if raw_response.startswith("```"):
                        raw_response = raw_response[3:]
                    if raw_response.endswith("```"):
                        raw_response = raw_response[:-3]
                    raw_response = raw_response.strip()
                    
                    try:
                        extracted_topics = json.loads(raw_response)
                        if not isinstance(extracted_topics, list):
                            # In case it returned a single object, wrap it in a list
                            extracted_topics = [extracted_topics]
                    except Exception as e:
                        print(f"JSON parsing failed for {filename}: {e}")
                        extracted_topics = [{"title": os.path.splitext(filename)[0], "category": "Meta", "content": content}]
                    
                    for topic in extracted_topics:
                        if not isinstance(topic, dict):
                            continue
                        
                        raw_title = topic.get("title", "Untitled")
                        # Sanitize title for filename
                        safe_title = "".join(c for c in raw_title if c.isalnum() or c in (' ', '_', '-')).strip()
                        safe_title = safe_title.replace(" ", "_")
                        if not safe_title:
                            safe_title = "Untitled"
                            
                        category = topic.get("category", "Meta")
                        formatted_content = topic.get("content", content)
                        
                        if isinstance(formatted_content, dict) or isinstance(formatted_content, list):
                            formatted_content = json.dumps(formatted_content, indent=2)
                        elif not isinstance(formatted_content, str):
                            formatted_content = str(formatted_content)
                        
                        # Fuzzy match category
                        matched_category = "Meta"
                        for cat in categories:
                            if category.lower() in cat.lower() or cat.lower() in category.lower():
                                matched_category = cat
                                break
                        category = matched_category
                        
                        # Save to the categorized folder
                        cat_dir = os.path.join(self.lore_dir, category)
                        os.makedirs(cat_dir, exist_ok=True)
                        dest_path = os.path.join(cat_dir, f"{safe_title}.md")
                        
                        # Handle duplicate filenames
                        counter = 1
                        while os.path.exists(dest_path):
                            dest_path = os.path.join(cat_dir, f"{safe_title}_{counter}.md")
                            counter += 1
                        
                        with open(dest_path, "w", encoding="utf-8") as out_f:
                            out_f.write(formatted_content)
                            
                        # PHASE 2: Knowledge Base Extraction
                        kb_prompt = (
                            "Extract structured relational data from the following text.\n"
                            "Return a JSON object containing THREE arrays: 'factions', 'settlements', and 'inconsistencies'.\n"
                            "Factions: {\"name\": string, \"treasury\": float, \"tech_level\": int}\n"
                            "Settlements: {\"name\": string, \"population\": int, \"faction_name\": string}\n"
                            "Inconsistencies: {\"description\": string}\n"
                            "If there are none, return an empty array for that key. ONLY output the JSON object."
                        )
                        kb_data = json.dumps({
                            "model": self.model,
                            "prompt": f"System: {kb_prompt}\n\nUser: {formatted_content}",
                            "stream": False,
                            "format": "json"
                        }).encode("utf-8")
                        
                        try:
                            kb_req = urllib.request.Request(
                                "http://localhost:11434/api/generate",
                                data=kb_data,
                                headers={"Content-Type": "application/json"},
                                method="POST"
                            )
                            with urllib.request.urlopen(kb_req, timeout=300) as kb_resp:
                                kb_resp_data = json.loads(kb_resp.read().decode("utf-8"))
                                kb_raw_response = kb_resp_data.get("response", "{}").strip()
                                
                                if kb_raw_response.startswith("```json"):
                                    kb_raw_response = kb_raw_response[7:]
                                if kb_raw_response.startswith("```"):
                                    kb_raw_response = kb_raw_response[3:]
                                if kb_raw_response.endswith("```"):
                                    kb_raw_response = kb_raw_response[:-3]
                                kb_raw_response = kb_raw_response.strip()
                                
                                kb_result = json.loads(kb_raw_response)
                                
                                import sqlite3
                                conn = sqlite3.connect(self.db_path)
                                cursor = conn.cursor()
                                
                                # Ensure tables exist
                                cursor.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, title TEXT, content TEXT, category TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                                cursor.execute("CREATE TABLE IF NOT EXISTS factions (id INTEGER PRIMARY KEY, name TEXT, treasury REAL DEFAULT 0.0, tech_level INTEGER DEFAULT 1, color TEXT DEFAULT '#ffffff')")
                                cursor.execute("CREATE TABLE IF NOT EXISTS settlements (id INTEGER PRIMARY KEY, name TEXT, q INTEGER, r INTEGER, population INTEGER DEFAULT 1000, faction_id INTEGER)")
                                cursor.execute("CREATE TABLE IF NOT EXISTS inconsistencies (id INTEGER PRIMARY KEY, source_type TEXT, source_id TEXT, description TEXT, status TEXT DEFAULT 'open', detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                                cursor.execute("INSERT INTO notes (title, content, category) VALUES (?, ?, ?)", (safe_title, formatted_content, category))
                                
                                for faction in kb_result.get("factions", []):
                                    name = faction.get("name", "Unknown")
                                    if name and name != "Unknown":
                                        cursor.execute("INSERT INTO factions (name, treasury, tech_level) VALUES (?, ?, ?)", 
                                            (name, faction.get("treasury", 0.0), faction.get("tech_level", 1)))
                                
                                for settlement in kb_result.get("settlements", []):
                                    name = settlement.get("name", "Unknown")
                                    if name and name != "Unknown":
                                        cursor.execute("INSERT INTO settlements (name, population) VALUES (?, ?)", 
                                            (name, settlement.get("population", 1000)))
                                
                                for inc in kb_result.get("inconsistencies", []):
                                    desc = inc.get("description", "")
                                    if desc:
                                        cursor.execute("INSERT INTO inconsistencies (source_type, source_id, description) VALUES (?, ?, ?)", 
                                            ("note", safe_title, desc))
                                        
                                conn.commit()
                                conn.close()
                        except Exception as e:
                            print(f"Failed to extract KB data for {safe_title}: {e}")
                          
            except Exception as e:
                print(f"Error ingesting {filename}: {e}")
                self.error_occurred.emit(str(e))
                
        self.ingestion_complete.emit()

class AILoreDriverWorker(QThread):
    prompt_ready = pyqtSignal(str, str, str) # title, subheading, prompt_text
    
    def __init__(self, lore_dir, db_path, model="qwen2.5:latest", genre="Fantasy"):
        super().__init__()
        self.lore_dir = lore_dir
        self.db_path = db_path
        self.model = model
        self.genre = genre
        
    def run(self):
        try:
            target_file = None
            target_subheading = None
            
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Query for open inconsistencies
            cursor.execute("SELECT source_id, description FROM inconsistencies WHERE status='open' LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            
            if row:
                target_file = row[0]
                target_subheading = "Lore Gap"
                gap_description = row[1]
                title = target_file
            else:
                return # No gaps found
                
            system_prompt = (
                f"You are Worldsmith AI, an active worldbuilding director in a {self.genre} setting.\n"
                f"The user has a structural inconsistency or lore gap regarding '{title}': '{gap_description}'.\n"
                "Ask exactly ONE short, probing question to encourage the user to fill out this missing detail or fix the contradiction.\n"
                "CRITICAL: Do NOT answer the question yourself. Do not write creative content. Ask only the question."
            )
            
            import urllib.request
            import json
            
            data = json.dumps({
                "model": self.model,
                "prompt": f"System: {system_prompt}\n\nUser: I have a lore gap in {title}: {gap_description}. Ask me a question to help fix it.",
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

class AISpatialExtractorWorker(QThread):
    extraction_complete = pyqtSignal(str) # JSON string array
    error_occurred = pyqtSignal(str)

    def __init__(self, notes_content, model="qwen2.5:latest"):
        super().__init__()
        self.notes_content = notes_content
        self.model = model

    def run(self):
        try:
            system_prompt = (
                "You are a strict data extraction system for a map generator."
                "You must read the following notes and output a STRICT JSON array of objects representing geographical features.\n"
                "EACH object must have: \n"
                "- 'id': A unique string id.\n"
                "- 'type': The type of feature ('mountain', 'desert', 'ocean', 'forest', 'lake').\n"
                "- 'constraints': A list of constraint objects, e.g. [{'relation': 'north_of', 'target_id': 'some_other_id'}].\n"
                "Valid relations: 'north_of', 'south_of', 'east_of', 'west_of'.\n"
                "ONLY output valid JSON. No markdown, no explanations."
            )

            import urllib.request
            import json

            data = json.dumps({
                "model": self.model,
                "prompt": f"System: {system_prompt}\n\nUser: Extract from these notes:\n{self.notes_content}",
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
                result = resp_data.get("response", "").strip()
                self.extraction_complete.emit(result)
                
        except Exception as e:
            self.error_occurred.emit(str(e))
