import os
import re

filepath = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\core\ai_worker.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# We want to replace the schema definition and the extraction loop
# Since it's large, I'll use regex to replace it

start_marker = "        dissection_schema = {"
end_marker = '                cursor.execute("UPDATE notes SET category=? WHERE id=?", (final_category, note_id))\n                conn.commit()'

new_block = '''
        system_instruction = f"""
You are a master relational parser of {self.genre} lore.
Extract entities and atomic facts from the text.
Do NOT output JSON. Output only structured Markdown lists EXACTLY in this format:

## Category
[Main Category of the text, e.g. Factions, Characters, Locations, Religions, Economy, General]

## Entities
- [Faction] Name : Description
- [Character] Name : Description
- [Location] Name : Description
- [Religion] Name : Description
- [Economy] Resource Name : Description

## Facts
- Subject | Relationship | Target | Context
"""

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
                
                # Save full text to database first for immediate searchability
                conn = sqlite3.connect(self.db_path, timeout=15.0)
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO notes (title, content, category)
                    VALUES (?, ?, ?)
                    ON CONFLICT(title) DO UPDATE SET content=excluded.content
                """, (title, raw_prose, "General"))
                
                cursor.execute("SELECT id FROM notes WHERE title=?", (title,))
                note_id = cursor.fetchone()[0]

                # Process chunks
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

                for c_idx, chunk_text in enumerate(chunks):
                    self.progress_update.emit(idx + 1, total_files, f"{filename} (Chunk {c_idx+1}/{len(chunks)})")
                    
                    prompt = f"Extract worldbuilding entities from this text snippet:\\n\\n{chunk_text}"
                    resp = LordsmithAIClient.execute_prompt(
                        prompt,
                        system_instruction=system_instruction
                    )

                    clean_resp = resp.strip()
                    if "AI Ingestion Engine Error" in clean_resp:
                        raise Exception("AI backend unreachable for this chunk (Rate limit or timeout).")
                    
                    # Regex parsing of the markdown output
                    lines = clean_resp.split('\\n')
                    mode = None
                    for line in lines:
                        line = line.strip()
                        if line.startswith("## Category"):
                            mode = "category"
                        elif line.startswith("## Entities"):
                            mode = "entities"
                        elif line.startswith("## Facts"):
                            mode = "facts"
                        elif line.startswith("-") or line.startswith("*"):
                            line = line.lstrip("-* ").strip()
                            if mode == "category":
                                final_category = line
                            elif mode == "entities":
                                m = re.match(r"^\\[(.*?)\\](.*?):(.*)", line)
                                if m:
                                    e_type = m.group(1).strip().lower()
                                    e_name = m.group(2).strip()
                                    e_desc = m.group(3).strip()
                                    if e_type == "faction":
                                        cursor.execute("INSERT INTO factions (name, color, associated_note_id) VALUES (?, '#3b82f6', ?) ON CONFLICT(name) DO NOTHING", (e_name, note_id))
                                    elif e_type == "character":
                                        cursor.execute("INSERT INTO actors (name, associated_note_id) VALUES (?, ?)", (e_name, note_id))
                                    elif e_type == "location":
                                        cursor.execute("INSERT INTO settlements (name, associated_note_id) VALUES (?, ?)", (e_name, note_id))
                                    elif e_type == "religion":
                                        cursor.execute("INSERT INTO religions (name, color, associated_note_id) VALUES (?, '#eab308', ?) ON CONFLICT(name) DO NOTHING", (e_name, note_id))
                            elif mode == "facts":
                                parts = [p.strip() for p in line.split("|")]
                                if len(parts) >= 3:
                                    subject = parts[0]
                                    rel = parts[1]
                                    target = parts[2]
                                    context = parts[3] if len(parts) > 3 else ""
                                    cursor.execute("INSERT INTO atomic_facts (subject, relationship, target, context, associated_note_id) VALUES (?, ?, ?, ?, ?)", (subject, rel, target, context, note_id))
                                    
                cursor.execute("UPDATE notes SET category=? WHERE id=?", (final_category, note_id))
                conn.commit()
'''

if start_marker in content and end_marker in content:
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker) + len(end_marker)
    new_content = content[:start_idx] + new_block.strip("\n") + "\n" + content[end_idx:]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully patched ai_worker.py to use robust Markdown Regex Parsing.")
else:
    print("Could not find markers.")
