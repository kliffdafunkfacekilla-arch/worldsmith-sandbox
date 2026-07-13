import os

filepath = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\core\ai_worker.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """        for idx, file_path in enumerate(self.file_paths):
            filename = os.path.basename(file_path)
            self.progress_update.emit(idx + 1, total_files, filename)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_prose = f.read()

                if self.ai_offline:
                    raise Exception("AI backend known to be offline. Skipping API call.")

                prompt = f"Dissect and extract worldbuilding entities from this text:\\n\\n{raw_prose}"
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
                category = dissected_data.get("category", "General")

                self.commit_dissected_nodes(file_path, category, dissected_data, raw_prose)

                dest_path = os.path.join(self.vault_dir, category, filename)
                with open(dest_path, "w", encoding="utf-8") as dest_f:
                    dest_f.write(raw_prose)

            except Exception as e:
                print(f"Skipping JSON entity extraction for {filename}: {e}")
                
                try:
                    category = "General"
                    self.commit_dissected_nodes(file_path, category, {}, raw_prose)
                    dest_path = os.path.join(self.vault_dir, category, filename)
                    with open(dest_path, "w", encoding="utf-8") as dest_f:
                        dest_f.write(raw_prose)
                    print(f"-> Successfully saved {filename} as a raw offline note instead.")
                except Exception as ex2:
                    print(f"-> Critical failure saving raw note {filename}: {ex2}")

            self.msleep(100)

        self.ingestion_complete.emit(not getattr(self, 'ai_offline', False))

    def commit_dissected_nodes(self, original_path, category, data, content):
        title = os.path.splitext(os.path.basename(original_path))[0]
        try:
            conn = sqlite3.connect(self.db_path, timeout=15.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()

            cursor.execute(\"\"\"
                INSERT INTO notes (title, content, category)
                VALUES (?, ?, ?)
                ON CONFLICT(title) DO UPDATE SET content=excluded.content, category=excluded.category
            \"\"\", (title, content, category))
            note_id = cursor.lastrowid if cursor.lastrowid else 1

            if "faction" in data and data["faction"].get("name"):
                f = data["faction"]
                cursor.execute(\"\"\"
                    INSERT INTO factions (name, color, gov_type, magic_stance, domain_type, associated_note_id)
                    VALUES (?, '#3b82f6', ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET gov_type=excluded.gov_type
                \"\"\", (f["name"], f.get("gov_type", "Empire"), f.get("magic_stance", "Regulated"), f.get("domain_type", "Both"), note_id))

            if "religion" in data and data["religion"].get("name"):
                r = data["religion"]
                cursor.execute(\"\"\"
                    INSERT INTO religions (name, color, religion_type, supreme_deity, associated_note_id)
                    VALUES (?, '#eab308', ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET supreme_deity=excluded.supreme_deity
                \"\"\", (r["name"], r.get("religion_type", "Deity-Centric"), r.get("supreme_deity", "Solis"), note_id))

            if "settlement" in data and data["settlement"].get("name"):
                s = data["settlement"]
                cursor.execute(\"\"\"
                    INSERT INTO settlements (name, population, cell_idx, associated_note_id)
                    VALUES (?, ?, ?, ?)
                \"\"\", (s["name"], s.get("population_k", 10.0), random.randint(100, 900), note_id))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error mapping entity rows: {e}")"""

new_block = """        for idx, file_path in enumerate(self.file_paths):
            filename = os.path.basename(file_path)
            self.progress_update.emit(idx + 1, total_files, filename)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_prose = f.read()

                if self.ai_offline:
                    raise Exception("AI backend known to be offline. Skipping API call.")

                title = os.path.splitext(filename)[0]
                
                # CHUNKING LOGIC: Split by double newline, group into ~800 word chunks
                paragraphs = raw_prose.split('\\n\\n')
                chunks = []
                current_chunk = []
                current_words = 0
                for p in paragraphs:
                    words = len(p.split())
                    if current_words + words > 800 and current_chunk:
                        chunks.append('\\n\\n'.join(current_chunk))
                        current_chunk = [p]
                        current_words = words
                    else:
                        current_chunk.append(p)
                        current_words += words
                if current_chunk:
                    chunks.append('\\n\\n'.join(current_chunk))

                final_category = "General"
                
                # Save full text to database first
                conn = sqlite3.connect(self.db_path, timeout=15.0)
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                cursor.execute(\"\"\"
                    INSERT INTO notes (title, content, category)
                    VALUES (?, ?, ?)
                    ON CONFLICT(title) DO UPDATE SET content=excluded.content, category=excluded.category
                \"\"\", (title, raw_prose, final_category))
                
                cursor.execute("SELECT id FROM notes WHERE title=?", (title,))
                note_id = cursor.fetchone()[0]

                # Process each chunk
                for c_idx, chunk_text in enumerate(chunks):
                    self.progress_update.emit(idx + 1, total_files, f"{filename} (Chunk {c_idx+1}/{len(chunks)})")
                    
                    prompt = f"Dissect and extract worldbuilding entities from this text snippet:\\n\\n{chunk_text}"
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
                    if dissected_data.get("category") and dissected_data["category"] != "General":
                        final_category = dissected_data["category"]

                    if "faction" in dissected_data and dissected_data["faction"].get("name"):
                        f = dissected_data["faction"]
                        cursor.execute(\"\"\"
                            INSERT INTO factions (name, color, gov_type, magic_stance, domain_type, associated_note_id)
                            VALUES (?, '#3b82f6', ?, ?, ?, ?)
                            ON CONFLICT(name) DO UPDATE SET gov_type=excluded.gov_type
                        \"\"\", (f["name"], f.get("gov_type", "Empire"), f.get("magic_stance", "Regulated"), f.get("domain_type", "Both"), note_id))

                    if "religion" in dissected_data and dissected_data["religion"].get("name"):
                        r = dissected_data["religion"]
                        cursor.execute(\"\"\"
                            INSERT INTO religions (name, color, religion_type, supreme_deity, associated_note_id)
                            VALUES (?, '#eab308', ?, ?, ?)
                            ON CONFLICT(name) DO UPDATE SET supreme_deity=excluded.supreme_deity
                        \"\"\", (r["name"], r.get("religion_type", "Deity-Centric"), r.get("supreme_deity", "Solis"), note_id))

                    if "settlement" in dissected_data and dissected_data["settlement"].get("name"):
                        s = dissected_data["settlement"]
                        cursor.execute(\"\"\"
                            INSERT INTO settlements (name, population, cell_idx, associated_note_id)
                            VALUES (?, ?, ?, ?)
                        \"\"\", (s["name"], s.get("population_k", 10.0), random.randint(100, 900), note_id))

                cursor.execute("UPDATE notes SET category=? WHERE id=?", (final_category, note_id))
                conn.commit()
                conn.close()

                dest_path = os.path.join(self.vault_dir, final_category, filename)
                with open(dest_path, "w", encoding="utf-8") as dest_f:
                    dest_f.write(raw_prose)

            except Exception as e:
                print(f"Skipping JSON entity extraction for {filename}: {e}")
                
                try:
                    category = "General"
                    conn = sqlite3.connect(self.db_path, timeout=15.0)
                    conn.execute("PRAGMA journal_mode=WAL;")
                    cursor = conn.cursor()
                    cursor.execute(\"\"\"
                        INSERT INTO notes (title, content, category)
                        VALUES (?, ?, ?)
                        ON CONFLICT(title) DO UPDATE SET content=excluded.content, category=excluded.category
                    \"\"\", (os.path.splitext(filename)[0], raw_prose, category))
                    conn.commit()
                    conn.close()

                    dest_path = os.path.join(self.vault_dir, category, filename)
                    with open(dest_path, "w", encoding="utf-8") as dest_f:
                        dest_f.write(raw_prose)
                    print(f"-> Successfully saved {filename} as a raw offline note instead.")
                except Exception as ex2:
                    print(f"-> Critical failure saving raw note {filename}: {ex2}")

            self.msleep(100)

        self.ingestion_complete.emit(not getattr(self, 'ai_offline', False))"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Chunking Updated')
else:
    print('Could not find chunking block')
