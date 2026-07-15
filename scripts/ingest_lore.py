import os
import sqlite3
import hashlib
import re
import sys

# Ensure python_fmg is in path to import LordsmithAIClient (acting as AiWorker)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from python_fmg.core.ai_worker import LordsmithAIClient

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lore_forge_world.db"))
VAULT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lore_vault"))

def init_db():
    """Phase 3 Setup: Ensure file_hashes and actors tables exist with proper columns."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. file_hashes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_hashes (
            file_path TEXT PRIMARY KEY,
            md5_hash TEXT
        )
    """)
    
    # 2. actors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            school TEXT,
            element TEXT,
            dragon_form TEXT,
            historical_note TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_file_hash(filepath):
    """Calculates the MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def extract_regex_data(content):
    """Phase 1: Zero-Cost Regex Parsing (The Heavy Lifting)"""
    extracted_data = []
    
    # Split the document by headers to isolate entities
    sections = re.split(r'(?m)^(?=#{1,6}\s+)', content)
    
    for section in sections:
        # Check if this section contains table attributes
        if "| Attribute | Detail |" in section:
            data = {}
            
            # Target 2: Extract the name (from the # Header)
            name_match = re.search(r'^#{1,6}\s+(.*)', section)
            if name_match:
                data['name'] = name_match.group(1).strip()
            
            # Extract school
            school_match = re.search(r'\|\s*\*\*School\*\*\s*\|\s*(?:\[\[)?(.*?)?(?:\]\])?\s*\|', section, re.IGNORECASE)
            if school_match:
                data['school'] = school_match.group(1).replace('[', '').replace(']', '').strip()
                
            # Extract element
            element_match = re.search(r'\|\s*\*\*Element\*\*\s*\|\s*(.*?)\s*\|', section, re.IGNORECASE)
            if element_match:
                data['element'] = element_match.group(1).strip()
                
            # Extract dragon_form
            dragon_match = re.search(r'\|\s*\*\*Dragon Form\*\*\s*\|\s*(?:\[\[)?(.*?)?(?:\]\])?\s*\|', section, re.IGNORECASE)
            if dragon_match:
                data['dragon_form'] = dragon_match.group(1).replace('[', '').replace(']', '').strip()
                
            # Target 3: Find any linked entities
            links = re.findall(r'\[\[(.*?)\]\]', section)
            data['links'] = list(set(links))
            
            # Target 4: Extract remaining narrative prose
            # Remove the table block
            prose = re.sub(r'(?m)^\|.*\|$', '', section)
            # Clean up extra newlines and header
            prose = re.sub(r'^#{1,6}\s+.*', '', prose)
            prose = re.sub(r'\n{3,}', '\n\n', prose).strip()
            data['raw_text'] = prose
            
            if 'name' in data:
                extracted_data.append(data)
                
    return extracted_data

def summarize_prose(entity_name, raw_text):
    """Phase 2: Targeted Local Summarization (The AI Component)"""
    if not raw_text.strip():
        return ""
        
    prompt = f"You are a lore archivist. Read the following text about {entity_name}. Summarize their history and tyranny into a single, concise 3-sentence historical note. Do not use markdown, formatting, or conversational filler. Return only the plain string.\n\nText:\n{raw_text}"
    
    try:
        # We pass api_key="" to STRICTLY force the AiWorker to use the local Ollama instance
        # and entirely bypass Gemini and other cloud APIs as per the instructions!
        response = LordsmithAIClient.execute_prompt(prompt, api_key="", model_name="qwen2.5:latest")
        if response:
            return response.strip()
    except Exception as e:
        print(f"Error during summarization for {entity_name}: {e}")
    return ""

def main():
    """Phase 3: Hash Caching & Database Commits"""
    print("Starting Strictly Local Hybrid Data Extraction Pipeline...")
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    processed_count = 0
    skipped_count = 0
    
    # The Loop: For every .md file in lore_vault/
    for root, _, files in os.walk(VAULT_DIR):
        for file in files:
            if file.endswith('.md'):
                filepath = os.path.join(root, file)
                
                # Calculate its MD5 hash
                current_hash = get_file_hash(filepath)
                
                # Check file_hashes table
                cursor.execute("SELECT md5_hash FROM file_hashes WHERE file_path = ?", (filepath,))
                row = cursor.fetchone()
                
                # If the hash matches, continue (skip the file entirely)
                if row and row[0] == current_hash:
                    print(f"Skipping {file} (No changes)")
                    skipped_count += 1
                    continue
                    
                print(f"Processing {file}...")
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # If the hash is new, run Phase 1 and Phase 2
                extracted_entities = extract_regex_data(content)
                
                for entity in extracted_entities:
                    name = entity.get('name')
                    school = entity.get('school', '')
                    element = entity.get('element', '')
                    dragon = entity.get('dragon_form', '')
                    raw_text = entity.get('raw_text', '')
                    
                    summary = summarize_prose(name, raw_text)
                    
                    # Use INSERT ... ON CONFLICT(name) DO UPDATE
                    cursor.execute("""
                        INSERT INTO actors (name, school, element, dragon_form, historical_note)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(name) DO UPDATE SET 
                            school=excluded.school, 
                            element=excluded.element, 
                            dragon_form=excluded.dragon_form,
                            historical_note=excluded.historical_note
                    """, (name, school, element, dragon, summary))
                
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
