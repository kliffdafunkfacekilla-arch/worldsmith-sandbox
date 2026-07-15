import os
import sqlite3
import hashlib
import re

DB_PATH = "lore_forge_world.db"
LORE_DIR = "lore_vault" # Change this to wherever your markdown files are

def init_db():
    """Ensures the caching table and core extraction tables exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Hash table to prevent re-processing unchanged files
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_hashes (
            file_path TEXT PRIMARY KEY,
            md5_hash TEXT
        )
    """)
    
    # Core world tables (if they don't exist yet)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            original_title TEXT,
            school TEXT,
            element TEXT,
            dragon_form TEXT
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

def extract_magistar_data(content):
    """Uses Regex to pull exact stats from the Markdown tables."""
    extracted = []
    
    # Split the document by the "Master Lore:" headers
    sections = re.split(r'## Master Lore:', content)
    
    for section in sections:
        # Check if this section is about a Magistar
        if "Magistar" in section and "| Attribute | Detail |" in section:
            data = {}
            
            # Extract Name (Assuming it's the main Header #)
            name_match = re.search(r'# (Magistar .*?)\n', section)
            if name_match:
                data['name'] = name_match.group(1).strip()
            
            # Extract School from the table row
            school_match = re.search(r'\|\s*\*\*School\*\*\s*\|\s*(?:\[\[)?(.*?)(?:\]\])?\s*\|', section)
            if school_match:
                # Cleans up things like "[[Flux1]] (Finesse)"
                data['school'] = school_match.group(1).replace('[', '').replace(']', '').strip()
                
            # Extract Element
            element_match = re.search(r'\|\s*\*\*Element\*\*\s*\|\s*(.*?)\s*\|', section)
            if element_match:
                data['element'] = element_match.group(1).strip()
                
            # Extract Dragon Form
            dragon_match = re.search(r'\|\s*\*\*Dragon Form\*\*\s*\|\s*(?:\[\[)?(.*?)(?:\]\])?\s*\|', section)
            if dragon_match:
                data['dragon_form'] = dragon_match.group(1).replace('[', '').replace(']', '').strip()
                
            if 'name' in data:
                extracted.append(data)
                
    return extracted

def ingest_to_db(magistar_data):
    """Writes the extracted structured data into SQLite."""
    if not magistar_data:
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for mag in magistar_data:
        cursor.execute("""
            INSERT INTO actors (name, school, element, dragon_form)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET 
                school=excluded.school, 
                element=excluded.element, 
                dragon_form=excluded.dragon_form
        """, (mag.get('name'), mag.get('school'), mag.get('element'), mag.get('dragon_form')))
        
    conn.commit()
    conn.close()

def main():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Walk through all markdown files
    for root, _, files in os.walk(LORE_DIR):
        for file in files:
            if file.endswith(".md"):
                filepath = os.path.join(root, file)
                current_hash = get_file_hash(filepath)
                
                # Check if file has changed
                cursor.execute("SELECT md5_hash FROM file_hashes WHERE file_path = ?", (filepath,))
                row = cursor.fetchone()
                
                if row and row[0] == current_hash:
                    print(f"Skipping {file} (No changes)")
                    continue
                
                print(f"Processing {file}...")
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract and Ingest
                magistars = extract_magistar_data(content)
                ingest_to_db(magistars)
                
                # Update Hash Cache
                cursor.execute("""
                    INSERT INTO file_hashes (file_path, md5_hash) 
                    VALUES (?, ?) 
                    ON CONFLICT(file_path) DO UPDATE SET md5_hash=excluded.md5_hash
                """, (filepath, current_hash))
                conn.commit()
                
    conn.close()
    print("Lore Ingestion Complete.")

if __name__ == "__main__":
    main()
