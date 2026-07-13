import os
import sqlite3
import json
from dotenv import load_dotenv

load_dotenv()
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

class AIBootstrapperWorker(QThread):
    """
    Background worker that runs on app startup to ensure the Ollama server is running
    and explicitly pre-loads the heavy AI model into system memory so that future
    ingestion requests are instantaneous.
    """
    boot_complete = pyqtSignal(bool, str) # success, message

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            # 1. Check if Ollama daemon is already running
            server_running = False
            try:
                urllib.request.urlopen("http://127.0.0.1:11434/", timeout=2)
                server_running = True
            except:
                pass

            if not server_running:
                import subprocess
                # Start Ollama silently in the background
                creation_flags = 0x08000000 # CREATE_NO_WINDOW on Windows
                subprocess.Popen(["ollama", "serve"], creationflags=creation_flags)
                time.sleep(5) # Wait for daemon to bind to port

            # 2. Pre-load the model into RAM
            # Sending an empty generate request forces Ollama to pull the model from disk to RAM
            payload = {"model": "qwen2.5:latest"}
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            
            # This loading phase can take 30-120 seconds on a CPU, which is why we do it in a QThread on startup!
            with urllib.request.urlopen(req, timeout=180) as response:
                pass

            self.boot_complete.emit(True, "Local AI Engine is Online and Model is Loaded into RAM.")
        except Exception as e:
            self.boot_complete.emit(False, f"AI Boot bypassed. Running in offline/fallback mode. ({str(e)})")


class LordsmithAIClient:
    """
    Unified communication bridge that executes requests against local Ollama 
    endpoints or Google Gemini API with mandatory exponential backoff and error handling.
    """
    @staticmethod
    def execute_prompt(prompt, system_instruction=None, json_schema=None, api_key=None, model_name="qwen2.5:latest"):
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY", "")
        """
        Sends inference request to the available backend. 
        Tries local Ollama first, falling back to Google Gemini if configured or needed.
        """
        # Changed to 127.0.0.1 to avoid Windows IPv6 localhost resolution timeouts
        ollama_url = "http://127.0.0.1:11434/api/generate"
        ollama_payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
        
        # FIX: Explicitly inject the schema into the system prompt for local LLMs
        if json_schema:
            ollama_payload["format"] = "json"
            schema_str = json.dumps(json_schema, indent=2)
            if system_instruction:
                ollama_payload["system"] = system_instruction + f"\n\nYou MUST return a single JSON object strictly conforming to the following JSON schema. Do not output anything outside of the JSON block:\n{schema_str}"
            else:
                ollama_payload["system"] = f"You MUST return a single JSON object strictly conforming to the following JSON schema. Do not output anything outside of the JSON block:\n{schema_str}"
        elif system_instruction:
            ollama_payload["system"] = system_instruction

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
            # Timeout is still large, but since model is preloaded on boot, this should be fast now.
            with urllib.request.urlopen(req, timeout=300) as response:
                if response.status == 200:
                    resp_data = json.loads(response.read().decode("utf-8"))
                    return _clean_response(resp_data.get("response", "").strip())
        except Exception as e:
            print(f"Ollama local inference bypassed: {e}")
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

        backoff_delays = [1, 2, 4, 8, 16]
        for attempt, delay in enumerate(backoff_delays):
            try:
                req = urllib.request.Request(
                    gemini_url,
                    data=json.dumps(contents_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=30) as response:
                    if response.status == 200:
                        resp_data = json.loads(response.read().decode("utf-8"))
                        text_resp = resp_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        return _clean_response(text_resp.strip())
            except urllib.error.HTTPError as he:
                if he.code in [400, 401, 403]:
                    break
            except Exception:
                pass
            
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
    audit_complete = pyqtSignal(list)

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

            cursor.execute("SELECT id, name, gov_type, magic_stance FROM factions")
            factions = cursor.fetchall()
            
            cursor.execute("SELECT id, name, local_magic_handling FROM provinces")
            provinces = cursor.fetchall()

            cursor.execute("SELECT name, population, cell_idx FROM settlements")
            settlements = cursor.fetchall()
            conn.close()

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

            try:
                clean_resp = resp.strip()
                if "AI Ingestion Engine Error" in clean_resp:
                    raise Exception("Auditor offline")
                anomalies = json.loads(clean_resp)
            except Exception:
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
    progress_update = pyqtSignal(int, int, str)
    ingestion_complete = pyqtSignal(bool)

    def __init__(self, file_paths, db_path, vault_dir, genre="Fantasy", parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.db_path = db_path
        self.vault_dir = vault_dir
        self.genre = genre

    def run(self):
        total_files = len(self.file_paths)
        
        categories = ["Characters", "Factions", "Locations", "Cultures", "Religions", "General"]
        for cat in categories:
            os.makedirs(os.path.join(self.vault_dir, cat), exist_ok=True)

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
                },
                "actor": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "faction_name": {"type": "STRING"},
                        "role": {"type": "STRING"}
                    }
                },
                "faction_economic_status": {
                    "type": "OBJECT",
                    "properties": {
                        "faction_name": {"type": "STRING"},
                        "good_name": {"type": "STRING"},
                        "status": {"type": "STRING", "enum": ["Surplus", "Deficit"]},
                        "urgency_multiplier": {"type": "NUMBER"}
                    }
                },
                "diplomacy_tension": {
                    "type": "OBJECT",
                    "properties": {
                        "faction_a": {"type": "STRING"},
                        "faction_b": {"type": "STRING"},
                        "diplomacy_score": {"type": "INTEGER"},
                        "treaty_status": {"type": "STRING"}
                    }
                },
                "atomic_facts": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "subject": {"type": "STRING"},
                            "relationship": {"type": "STRING"},
                            "target": {"type": "STRING"},
                            "context": {"type": "STRING"}
                        }
                    }
                }
            },
            "required": ["category"]
        }

        self.ai_offline = False

        for idx, file_path in enumerate(self.file_paths):
            filename = os.path.basename(file_path)
            self.progress_update.emit(idx + 1, total_files, filename)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_prose = f.read()

                if self.ai_offline:
                    raise Exception("AI backend known to be offline. Skipping API call.")

                title = os.path.splitext(filename)[0]
                
                # CHUNKING LOGIC: Split by double newline, group into ~800 word chunks
                paragraphs = raw_prose.split('\n\n')
                chunks = []
                current_chunk = []
                current_words = 0
                for p in paragraphs:
                    words = len(p.split())
                    if current_words + words > 800 and current_chunk:
                        chunks.append('\n\n'.join(current_chunk))
                        current_chunk = [p]
                        current_words = words
                    else:
                        current_chunk.append(p)
                        current_words += words
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))

                final_category = "General"
                
                # Save full text to database first
                conn = sqlite3.connect(self.db_path, timeout=15.0)
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO notes (title, content, category)
                    VALUES (?, ?, ?)
                    ON CONFLICT(title) DO UPDATE SET content=excluded.content, category=excluded.category
                """, (title, raw_prose, final_category))
                
                cursor.execute("SELECT id FROM notes WHERE title=?", (title,))
                note_id = cursor.fetchone()[0]

                # Process each chunk
                for c_idx, chunk_text in enumerate(chunks):
                    self.progress_update.emit(idx + 1, total_files, f"{filename} (Chunk {c_idx+1}/{len(chunks)})")
                    
                    prompt = f"Dissect and extract worldbuilding entities from this text snippet:\n\n{chunk_text}"
                    resp = LordsmithAIClient.execute_prompt(
                        prompt,
                        system_instruction=f"You are a master relational parser of {self.genre} lore. Output structured JSON blocks conforming to the requested schema.",
                        json_schema=dissection_schema
                    )

                    clean_resp = resp.strip()
                    if "AI Ingestion Engine Error" in clean_resp:
                        self.ai_offline = True
                        raise Exception("AI backend unreachable (No Ollama or API key).")
                    
                    dissected_data = json.loads(clean_resp)
                    if not dissected_data:
                        dissected_data = {}
                    if dissected_data.get("category") and dissected_data["category"] != "General":
                        final_category = dissected_data["category"]

                    if "faction" in dissected_data and dissected_data["faction"].get("name"):
                        f = dissected_data["faction"]
                        cursor.execute("""
                            INSERT INTO factions (name, color, gov_type, magic_stance, domain_type, associated_note_id)
                            VALUES (?, '#3b82f6', ?, ?, ?, ?)
                            ON CONFLICT(name) DO UPDATE SET gov_type=excluded.gov_type
                        """, (f["name"], f.get("gov_type", "Empire"), f.get("magic_stance", "Regulated"), f.get("domain_type", "Both"), note_id))

                    if "religion" in dissected_data and dissected_data["religion"].get("name"):
                        r = dissected_data["religion"]
                        cursor.execute("""
                            INSERT INTO religions (name, color, religion_type, supreme_deity, associated_note_id)
                            VALUES (?, '#eab308', ?, ?, ?)
                            ON CONFLICT(name) DO UPDATE SET supreme_deity=excluded.supreme_deity
                        """, (r["name"], r.get("religion_type", "Deity-Centric"), r.get("supreme_deity", "Solis"), note_id))

                    if "settlement" in dissected_data and dissected_data["settlement"].get("name"):
                        s = dissected_data["settlement"]
                        cursor.execute("""
                            INSERT INTO settlements (name, population, cell_idx, associated_note_id)
                            VALUES (?, ?, ?, ?)
                        """, (s["name"], s.get("population_k", 10.0), random.randint(100, 900), note_id))

                    if "actor" in dissected_data and dissected_data["actor"].get("name"):
                        a = dissected_data["actor"]
                        # Get faction id if possible
                        cursor.execute("SELECT id FROM factions WHERE name=?", (a.get("faction_name"),))
                        f_row = cursor.fetchone()
                        f_id = f_row[0] if f_row else None
                        cursor.execute("""
                            INSERT INTO actors (name, faction_id, current_cell_idx, is_alive, role)
                            VALUES (?, ?, ?, 1, ?)
                        """, (a["name"], f_id, random.randint(100, 900), a.get("role")))

                    if "faction_economic_status" in dissected_data and dissected_data["faction_economic_status"].get("faction_name"):
                        e = dissected_data["faction_economic_status"]
                        cursor.execute("SELECT id FROM factions WHERE name=?", (e.get("faction_name"),))
                        f_row = cursor.fetchone()
                        f_id = f_row[0] if f_row else None
                        if f_id:
                            cursor.execute("""
                                INSERT INTO faction_economics (faction_id, good_name, status, urgency_multiplier)
                                VALUES (?, ?, ?, ?)
                            """, (f_id, e.get("good_name"), e.get("status"), e.get("urgency_multiplier", 1.0)))

                    if "diplomacy_tension" in dissected_data and dissected_data["diplomacy_tension"].get("faction_a") and dissected_data["diplomacy_tension"].get("faction_b"):
                        d = dissected_data["diplomacy_tension"]
                        cursor.execute("SELECT id FROM factions WHERE name=?", (d.get("faction_a"),))
                        fa_row = cursor.fetchone()
                        cursor.execute("SELECT id FROM factions WHERE name=?", (d.get("faction_b"),))
                        fb_row = cursor.fetchone()
                        if fa_row and fb_row:
                            try:
                                cursor.execute("""
                                    INSERT INTO faction_relations (faction_a_id, faction_b_id, diplomacy_score, treaty_status)
                                    VALUES (?, ?, ?, ?)
                                """, (fa_row[0], fb_row[0], d.get("diplomacy_score", 0), d.get("treaty_status", "Neutral")))
                            except sqlite3.IntegrityError:
                                pass # Unique constraint failed, relation exists

                    if "atomic_facts" in dissected_data and isinstance(dissected_data["atomic_facts"], list):
                        for fact in dissected_data["atomic_facts"]:
                            if fact.get("subject") and fact.get("relationship") and fact.get("target"):
                                cursor.execute("""
                                    INSERT INTO atomic_facts (subject, relationship, target, context, associated_note_id)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (fact.get("subject"), fact.get("relationship"), fact.get("target"), fact.get("context", ""), note_id))

                cursor.execute("UPDATE notes SET category=? WHERE id=?", (final_category, note_id))
                conn.commit()
                conn.close()

                dest_path = os.path.join(self.vault_dir, final_category, filename)
                with open(dest_path, "w", encoding="utf-8") as dest_f:
                    dest_f.write(raw_prose)

            except Exception as e:
                print(f"Skipping JSON entity extraction for {filename}: {e}")
                # Ensure the primary connection is closed so we don't lock the database forever
                try:
                    if 'conn' in locals():
                        conn.close()
                except Exception:
                    pass
                
                try:
                    category = "General"
                    conn2 = sqlite3.connect(self.db_path, timeout=15.0)
                    conn2.execute("PRAGMA journal_mode=WAL;")
                    cursor2 = conn2.cursor()
                    cursor2.execute("""
                        INSERT INTO notes (title, content, category)
                        VALUES (?, ?, ?)
                        ON CONFLICT(title) DO UPDATE SET content=excluded.content, category=excluded.category
                    """, (os.path.splitext(filename)[0], raw_prose, category))
                    conn2.commit()
                    conn2.close()

                    dest_path = os.path.join(self.vault_dir, category, filename)
                    with open(dest_path, "w", encoding="utf-8") as dest_f:
                        dest_f.write(raw_prose)
                    print(f"-> Successfully saved {filename} as a raw offline note instead.")
                except Exception as ex2:
                    print(f"-> Critical failure saving raw note {filename}: {ex2}")

            self.msleep(100)

        self.ingestion_complete.emit(not getattr(self, 'ai_offline', False))


# =============================================================================
# WORKER: ACTIVE CONVERSATIONAL QUESTION GENERATOR
# =============================================================================
class AILoreDriverWorker(QThread):
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
