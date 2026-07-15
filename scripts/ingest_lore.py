import os
import sqlite3
import hashlib
import re
import sys

# Ensure python_fmg is in path to import LordsmithAIClient (acting as AiWorker)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from python_fmg.core.ai_worker import LordsmithAIClient

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lore_forge_world.db"))
VAULT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "lore_vault"))

def init_db():
    """Phase 3 Setup: Ensure file_hashes table exists."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. file_hashes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_hashes (
            file_path TEXT PRIMARY KEY,
            md5_hash TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def extract_regex_data(content):
    """Phase 1: General Zero-Cost Regex Parsing for All Subjects"""
    extracted_data = []
    
    # Split the document by major headers to isolate entities (either Master Lore, or level 1/2 headers)
    sections = re.split(r'(?m)^(?:## Master Lore:|# .*$|## .*$)', content)
    
    # We also need the headers themselves, so let's use finditer instead to get the full section block
    headers = list(re.finditer(r'(?m)^(?:## Master Lore:.*?$|# .*$|## .*$)', content))
    
    for i in range(len(headers)):
        header_text = headers[i].group(0)
        start = headers[i].end()
        end = headers[i+1].start() if i + 1 < len(headers) else len(content)
        
        section_content = content[start:end]
        full_section = header_text + "\n" + section_content
        
        data = {}
        
        # 1. Extract Name from the header itself
        name = re.sub(r'^(?:## Master Lore:|#|##)\s*', '', header_text).strip()
        name = re.sub(r'\(.*?\)', '', name).strip().replace('*', '').replace('"', '')
        if not name or "Table of Contents" in name or "Appendix" in name or "Chapter" in name:
            continue
        data['name'] = name
        
        # 2. Extract YAML Tags
        tags = []
        yaml_match = re.search(r'(?ms)^---.*?tags:\s*(.*?)^---', full_section)
        if yaml_match:
            tag_block = yaml_match.group(1)
            # Parse list format `[tag1, tag2]` or bullet `- tag`
            if '[' in tag_block:
                tags = [t.strip('\'"[] ') for t in tag_block.split(',')]
            else:
                tags = [t.strip('- \r\n') for t in tag_block.split('\n') if t.strip()]
        
        # If no yaml in this section, check if there's a global file yaml at the very beginning of content
        if not tags and i == 0:
            global_yaml = re.search(r'\A---\s*.*?tags:\s*(.*?)^---', content, re.MULTILINE | re.DOTALL)
            if global_yaml:
                tag_block = global_yaml.group(1)
                if '[' in tag_block:
                    tags = [t.strip('\'"[] ') for t in tag_block.split(',')]
                else:
                    tags = [t.strip('- \r\n') for t in tag_block.split('\n') if t.strip()]
                    
        data['tags'] = [t.lower() for t in tags if t]
        
        # 3. Extract Markdown Table Attributes
        table_rows = re.findall(r'\|\s*(.*?)\s*\|\s*(.*?)\s*\|', full_section)
        has_table = False
        for key, val in table_rows:
            k = key.replace('*', '').strip()
            v = val.replace('[', '').replace(']', '').strip()
            if k and k != "Attribute" and k != ":---" and k != "---":
                data[k] = v
                has_table = True
                
        # Skip generic narrative sections that aren't specific entities
        # A valid entity must have a table OR specific entity tags
        valid_tags = ['npc', 'character', 'faction', 'factions', 'hegemony', 'location', 'settlement', 'religion', 'culture']
        is_entity = has_table or any(t in valid_tags for t in data['tags'])
        
        if not is_entity:
            continue
            
        # 4. Find linked entities
        links = re.findall(r'\[\[(.*?)\]\]', full_section)
        data['links'] = list(set(links))
        
        # 5. Clean up Prose
        prose = re.sub(r'(?ms)^---.*?^---', '', full_section) # remove yaml
        prose = re.sub(r'(?m)^\|.*\|$', '', prose) # remove tables
        prose = re.sub(r'^#{1,6}\s+.*', '', prose, flags=re.MULTILINE) # remove headers
        prose = re.sub(r'>.*?$', '', prose, flags=re.MULTILINE) # remove blockquotes
        prose = re.sub(r'\n{3,}', '\n\n', prose).strip()
        data['raw_text'] = prose
        
        extracted_data.append(data)
                
    return extracted_data

def summarize_prose(entity_name, raw_text):
    """Phase 2: Targeted Local Summarization (The AI Component)"""
    if not raw_text.strip():
        return ""
        
    prompt = f"You are a lore archivist. Read the following text about {entity_name}. Summarize their history into a single, concise 3-sentence historical note. Do not use markdown, formatting, or conversational filler. Return only the plain string.\n\nText:\n{raw_text}"
    
    try:
        response = LordsmithAIClient.execute_prompt(prompt, api_key="", model_name="qwen2.5:latest")
        if response:
            return response.strip()
    except Exception as e:
        print(f"Error during summarization for {entity_name}: {e}")
    return ""

def main():
    """Phase 3: Hash Caching & Database Commits"""
    print("Starting Strictly Local Generalized Hybrid Data Extraction Pipeline...")
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    processed_count = 0
    skipped_count = 0
    
    for root, _, files in os.walk(VAULT_DIR):
        for file in files:
            if file.endswith('.md'):
                filepath = os.path.join(root, file)
                current_hash = get_file_hash(filepath)
                
                cursor.execute("SELECT md5_hash FROM file_hashes WHERE file_path = ?", (filepath,))
                row = cursor.fetchone()
                
                if row and row[0] == current_hash:
                    print(f"Skipping {file} (No changes)")
                    skipped_count += 1
                    continue
                    
                print(f"Processing {file}...")
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                extracted_entities = extract_regex_data(content)
                
                for entity in extracted_entities:
                    name = entity.get('name')
                    raw_text = entity.get('raw_text', '')
                    summary = summarize_prose(name, raw_text)
                    
                    # Smart Routing Based on Extracted Keys
                    keys = entity.keys()
                    table = "factions"
                    
                    if "School" in keys or "Role" in keys or "Former Master" in keys or "Species" in keys:
                        table = "actors"
                    elif "Capital" in keys or "Region" in keys or "Population" in keys or "Architecture" in keys:
                        table = "settlements"
                    elif "Pantheon" in keys or "Deity" in keys:
                        table = "religions"
                    elif "Tradition" in keys or "Origin" in keys:
                        table = "cultures"
                    else:
                        table = "factions"
                        
                    # Insert logic
                    try:
                        if table == "actors":
                            cursor.execute(
                                "INSERT INTO actors (name, historical_note) VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET historical_note=excluded.historical_note",
                                (name, summary)
                            )
                        elif table == "factions":
                            # Make sure factions name is unique via index if not already
                            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_factions_name ON factions(name)")
                            cursor.execute("INSERT INTO factions (name, color, description) VALUES (?, '#4b5563', ?) ON CONFLICT(name) DO UPDATE SET description=excluded.description", (name, summary))
                        elif table == "settlements":
                            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_settlements_name ON settlements(name)")
                            cursor.execute("INSERT INTO settlements (name, description) VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET description=excluded.description", (name, summary))
                        elif table == "religions":
                            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_religions_name ON religions(name)")
                            cursor.execute("INSERT INTO religions (name, color, description) VALUES (?, '#eab308', ?) ON CONFLICT(name) DO UPDATE SET description=excluded.description", (name, summary))
                        elif table == "cultures":
                            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_cultures_name ON cultures(name)")
                            cursor.execute("INSERT INTO cultures (name, description) VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET description=excluded.description", (name, summary))
                    except Exception as e:
                        print(f"Error inserting {name} into {table}: {e}")
                
                # Save the new MD5 hash to the file_hashes table
                cursor.execute("""
                    INSERT INTO file_hashes (file_path, md5_hash) 
                    VALUES (?, ?) 
                    ON CONFLICT(file_path) DO UPDATE SET md5_hash=excluded.md5_hash
                """, (filepath, current_hash))
                
                conn.commit()
                processed_count += 1
                
    conn.close()
    print(f"Pipeline complete! Processed: {processed_count}, Skipped: {skipped_count}")

if __name__ == "__main__":
    main()
