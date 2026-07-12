import os
import sqlite3
import json
import urllib.request
import urllib.error
import time
import random
import re
from PyQt6.QtCore import QThread, pyqtSignal

# =============================================================================
# TECH REFERENCE DOCUMENTATION LINKS:
# - Ollama API Specifications: https://github.com/ollama/ollama/blob/main/docs/api.md
# - Google Gemini API Reference: https://ai.google.dev/gemini-api/docs/quickstart
# - PyQt6 Multi-threading Guidelines: https://www.pyqt.org/static/v6-latest-release/index.html
# =============================================================================

class LordsmithAIClient:
    """
    Unified communication bridge that executes requests against local Ollama 
    endpoints or Google Gemini API with mandatory exponential backoff and error handling.
    """
    @staticmethod
    def execute_prompt(prompt, system_instruction=None, json_schema=None, api_key="", model_name="qwen2.5:latest"):
        """
        Sends inference request to the available backend. 
        Tries local Ollama first, falling back to Google Gemini if configured or needed.
        """
        # We try local Ollama first as the default offline desktop companion
        ollama_url = "http://localhost:11434/api/generate"
        ollama_payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
        if system_instruction:
            ollama_payload["system"] = system_instruction
        if json_schema:
            ollama_payload["format"] = "json"

        def _clean_response(text):
            if json_schema:
                text = re.sub(r'```json|```', '', text).strip()
            return text

        try:
            req = urllib.request.Request(
                ollama_url,
                data=json.dumps(ollama_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.status == 200:
                    resp_data = json.loads(response.read().decode("utf-8"))
                    return _clean_response(resp_data.get("response", "").strip())
        except Exception:
            # Local Ollama unavailable or timed out; fall back to Google Gemini API
            pass

        # === Google Gemini API Fallback Engine (gemini-2.5-flash-preview-09-2025) ===
        target_model = "gemini-2.5-flash-preview-09-2025"
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"
        
        contents_payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        if system_instruction:
            contents_payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        if json_schema:
            contents_payload["generationConfig"] = {
                "responseMimeType": "application/json",
                "responseSchema": json_schema
            }

        # 5-Stage Exponential Backoff Retry Loop
        backoff_delays = [1, 2, 4, 8, 16]
        for attempt, delay in enumerate(backoff_delays):
            try:
                req = urllib.request.Request(
                    gemini_url,
                    data=json.dumps(contents_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=12) as response:
                    if response.status == 200:
                        resp_data = json.loads(response.read().decode("utf-8"))
                        text_resp = resp_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        return _clean_response(text_resp.strip())
            except urllib.error.HTTPError as he:
                # If unauthorized or bad schema, do not retry blindly
                if he.code in [400, 401, 403]:
                    break
            except Exception:
                pass
            
            # Sleep silently without logging to console
            time.sleep(delay)

        return "AI Ingestion Engine Error: Offline model (Ollama) and cloud APIs are currently unreachable."


# =============================================================================
# WORKER: OLLAMA / GEMINI GENERAL PROMPT RUNNER
# =============================================================================
class OllamaPromptWorker(QThread):
    """Executes asynchronous, unblocked chat prompt queries."""
    response_received = pyqtSignal(str)

    def __init__(self, prompt, db_path="", genre="Fantasy", parent=None):
        super().__init__(parent)
        self.prompt = prompt
        self.genre = genre

    def run(self):
        system_instruction = f"You are Lordsmith AI, a master cartographer and chronicler of the {self.genre} genre. Provide immersive, rich advice."
        response = LordsmithAIClient.execute_prompt(self.prompt, system_instruction=system_instruction)
        self.response_received.emit(response)


# =============================================================================
# WORKER: METRIC LORE CONTRADICTION AUDITOR
# =============================================================================
class LoreAuditWorker(QThread):
    """
    Asynchronously cross-checks user's written prose against our active SQLite tables,
    flagging ecological, political, or jurisdictional contradictions.
    """
    audit_complete = pyqtSignal(list) # Returns list of string discrepancies

    def __init__(self, note_title, note_content, db_path, parent=None):
        super().__init__(parent)
        self.note_title = note_title
        self.note_content = note_content
        self.db_path = db_path

    def run(self):
        anomalies = []
        try:
            conn = sqlite3.connect(self.db_path, timeout=15.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()

            # Compile world state snapshot for the model
            cursor.execute("SELECT id, name, gov_type, magic_stance FROM factions")
            factions = cursor.fetchall()
            
            cursor.execute("SELECT id, name, local_magic_handling FROM provinces")
            provinces = cursor.fetchall()

            cursor.execute("SELECT name, population, cell_idx FROM settlements")
            settlements = cursor.fetchall()
            conn.close()

            # Format database state structurally
            db_summary = {
                "Sovereign Factions": [f"ID {f[0]}: {f[1]} ({f[2]}, Magic: {f[3]})" for f in factions],
                "Provinces": [f"ID {p[0]}: {p[1]} (Magic: {p[2]})" for p in provinces],
                "Active Cities": [f"{s[0]} (Pop: {s[1]}k, Cell: {s[2]})" for s in settlements]
            }

            prompt = f"""
            Identify any logical contradictions between the written lore below and our structured world database records.

            [World Database Snapshot]
            {json.dumps(db_summary, indent=2)}

            [Written Lore Note: "{self.note_title}"]
            {self.note_content}

            Analyze climate, geography, political boundaries, or magic rules.
            Output your audit results as a clean JSON list of strings representing discrepancies found. If none are found, return an empty JSON list [].
            """

            json_schema = {
                "type": "ARRAY",
                "items": {
                    "type": "STRING"
                }
            }

            resp = LordsmithAIClient.execute_prompt(
                prompt, 
                system_instruction="You are an automated Lore Consistency Auditor. Only output valid JSON arrays.",
                json_schema=json_schema
            )

            # Parse returned results safely
            try:
                clean_resp = resp.strip()
                anomalies = json.loads(clean_resp)
            except Exception:
                # Fallback simple line parsing if JSON parsing fails
                if resp and "Error" not in resp:
                    anomalies = [line.strip() for line in resp.split("\n") if line.strip()][:3]

        except Exception as e:
            anomalies = [f"Auditor bypass exception: {str(e)}"]

        self.audit_complete.emit(anomalies)


# =============================================================================
# WORKER: BULK DIRECTORY DISSECTION & EXTRACTION
# =============================================================================
class AILoreIngestor(QThread):
    """
    Scans a folder, processes notes asynchronously, dissects entities, 
    and raises completion signals matching PyQt expectations.
    """
    progress_update = pyqtSignal(int, int, str) # current, total, filename
    ingestion_complete = pyqtSignal()

    def __init__(self, file_paths, db_path, vault_dir, genre="Fantasy", parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.db_path = db_path
        self.vault_dir = vault_dir
        self.genre = genre

    def run(self):
        total_files = len(self.file_paths)
        
        # Build master subdirectories structure
        categories = ["Characters", "Factions", "Locations", "Cultures", "Religions", "General"]
        for cat in categories:
            os.makedirs(os.path.join(self.vault_dir, cat), exist_ok=True)

        # Define rigid JSON schema matching our 17 worldbuilding layers
        dissection_schema = {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "enum": ["Characters", "Factions", "Locations", "Cultures", "Religions", "General"]
                },
                "faction": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "gov_type": {"type": "STRING"},
                        "magic_stance": {"type": "STRING"},
                        "domain_type": {"type": "STRING"}
                    }
                },
                "religion": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "religion_type": {"type": "STRING"},
                        "supreme_deity": {"type": "STRING"}
                    }
                },
                "settlement": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "population_k": {"type": "NUMBER"}
                    }
                }
            },
            "required": ["category"]
        }

        for idx, file_path in enumerate(self.file_paths):
            filename = os.path.basename(file_path)
            self.progress_update.emit(idx + 1, total_files, filename)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_prose = f.read()

                # Extract entities matching our SQLite schemas
                prompt = f"Dissect and extract worldbuilding entities from this text:\n\n{raw_prose}"
                resp = LordsmithAIClient.execute_prompt(
                    prompt,
                    system_instruction=f"You are a master relational parser of {self.genre} lore. Output structured JSON blocks conforming to the requested schema.",
                    json_schema=dissection_schema
                )

                # Process raw reply
                clean_resp = resp.strip()
                dissected_data = json.loads(clean_resp)
                category = dissected_data.get("category", "General")

                # Sync parsed entries straight to SQLite
                self.commit_dissected_nodes(file_path, category, dissected_data, raw_prose)

                # Move note cleanly into its designated subdirectory
                dest_path = os.path.join(self.vault_dir, category, filename)
                with open(dest_path, "w", encoding="utf-8") as dest_f:
                    dest_f.write(raw_prose)

            except Exception as e:
                print(f"Skipping file {filename} due to parser exception: {e}")

            # Safe pacing sleep to allow progress bars to paint smoothly
            self.msleep(100)

        self.ingestion_complete.emit()

    def commit_dissected_nodes(self, original_path, category, data, content):
        """Pushes parsed entity structures safely to SQL using Foreign Key links."""
        title = os.path.splitext(os.path.basename(original_path))[0]
        try:
            conn = sqlite3.connect(self.db_path, timeout=15.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()

            # Insert raw note
            cursor.execute("""
                INSERT INTO notes (title, content, category)
                VALUES (?, ?, ?)
                ON CONFLICT(title) DO UPDATE SET content=excluded.content, category=excluded.category
            """, (title, content, category))
            note_id = cursor.lastrowid if cursor.lastrowid else 1

            # Insert parsed Factions
            if "faction" in data and data["faction"].get("name"):
                f = data["faction"]
                cursor.execute("""
                    INSERT INTO factions (name, color, gov_type, magic_stance, domain_type, associated_note_id)
                    VALUES (?, '#3b82f6', ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET gov_type=excluded.gov_type
                """, (f["name"], f.get("gov_type", "Empire"), f.get("magic_stance", "Regulated"), f.get("domain_type", "Both"), note_id))

            # Insert parsed Religions
            if "religion" in data and data["religion"].get("name"):
                r = data["religion"]
                cursor.execute("""
                    INSERT INTO religions (name, color, religion_type, supreme_deity, associated_note_id)
                    VALUES (?, '#eab308', ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET supreme_deity=excluded.supreme_deity
                """, (r["name"], r.get("religion_type", "Deity-Centric"), r.get("supreme_deity", "Solis"), note_id))

            # Insert parsed Settlements
            if "settlement" in data and data["settlement"].get("name"):
                s = data["settlement"]
                cursor.execute("""
                    INSERT INTO settlements (name, population, cell_idx, associated_note_id)
                    VALUES (?, ?, ?, ?)
                """, (s["name"], s.get("population_k", 10.0), random.randint(100, 900), note_id))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error mapping entity rows: {e}")


# =============================================================================
# WORKER: ACTIVE CONVERSATIONAL QUESTION GENERATOR
# =============================================================================
class AILoreDriverWorker(QThread):
    """Drives proactive active-learning conversational audits."""
    query_resolved = pyqtSignal(str)

    def __init__(self, system_state, parent=None):
        super().__init__(parent)
        self.state_summary = system_state

    def run(self):
        prompt = f"""
        Review our current worldbuilding state:
        {self.state_summary}

        Formulate exactly one proactive, narrative-driving question to help the creator
        expand their structural layers. Keep your response brief, engaging, and in-character as Lordsmith AI.
        """
        resp = LordsmithAIClient.execute_prompt(prompt, system_instruction="You are Lordsmith AI, driving campaign development.")
        self.query_resolved.emit(resp)
