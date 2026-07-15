import os
import sqlite3
import hashlib
import json
import re
import sys

# Ensure python_fmg is in path so we can import LordsmithAIClient
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from python_fmg.core.ai_worker import LordsmithAIClient

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lore_forge_world.db"))
VAULT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lore_vault"))
CACHE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".lore_cache.json"))

def get_file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=4)

def parse_markdown(content):
    # Phase 1: Pure Python Parsing
    
    # 1. Frontmatter
    tags = []
    aliases = []
    fm_match = re.search(r'^---\s*(.*?)\s*---', content, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        for line in fm_text.split('\n'):
            line = line.strip()
            if line.startswith('- '):
                tags.append(line[2:].strip())
            elif line.startswith('aliases:'):
                aliases_str = line.split('aliases:')[1].strip()
                if aliases_str:
                    aliases.extend([a.strip() for a in aliases_str.split(',')])

    # 2. Entity relationships (links)
    links = re.findall(r'\[\[(.*?)\]\]', content)
    unique_links = list(set(links))

    # 3. Hard stats from markdown tables
    # Matches simple markdown tables like:
    # | Attribute | Detail |
    # | --------- | ------ |
    # | School    | Fire   |
    stats = {}
    table_rows = re.findall(r'^\|(.+?)\|$', content, re.MULTILINE)
    for row in table_rows:
        if '---' in row:
            continue
        cols = [c.strip() for c in row.split('|')]
        if len(cols) == 2:
            stats[cols[0]] = cols[1]

    # Split into chunks by headers for narrative summarization
    chunks = re.split(r'(?m)^(?=#{1,6}\s+)', content)
    
    return tags, aliases, unique_links, stats, chunks

def summarize_narrative(chunk):
    # Phase 2: Targeted LLM Summarization
    prompt = f"Summarize the following historical narrative into a single concise paragraph. Return ONLY the summary string, nothing else.\n\nNarrative:\n{chunk}"
    try:
        response = LordsmithAIClient.execute_prompt(prompt, model_name="qwen2.5:latest")
        if response:
            return response.strip()
    except Exception as e:
        print(f"Error during summarization: {e}")
    return ""

def process_file(filepath, conn):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    tags, aliases, unique_links, stats, chunks = parse_markdown(content)
    
    cursor = conn.cursor()
    filename = os.path.basename(filepath)
    title = os.path.splitext(filename)[0]
    
    # Insert basic note record (Phase 1 Commit)
    cursor.execute("""
        INSERT INTO notes (title, content, category) 
        VALUES (?, ?, 'Lore') 
        ON CONFLICT(title) DO UPDATE SET content=excluded.content
    """, (title, content))
    
    # Optional: Insert tags if we had a many-to-many relationship table, but we can just store them as text
    
    # Phase 2: Process narrative chunks
    historical_notes = []
    for chunk in chunks:
        # Ignore very short chunks (e.g. just the header itself or whitespace)
        if len(chunk.strip()) > 100:
            summary = summarize_narrative(chunk)
            if summary:
                historical_notes.append(summary)
                
    combined_notes = "\n\n".join(historical_notes)
    
    # If the user specifically wants to append the historical note to `actors` or `factions` 
    # we would look for those entities. Since the prompt didn't specify which exact entity to update 
    # for arbitrary files, we update the Note or an associated Actor if one exists with this title.
    if combined_notes:
        cursor.execute("UPDATE notes SET content = content || ? WHERE title = ?", ("\n\n--- Historical Summary ---\n" + combined_notes, title))
        
        # Also attempt to update any actors with matching names
        cursor.execute("UPDATE actors SET historical_note = ? WHERE name = ?", (combined_notes, title))

    conn.commit()

def run_pipeline():
    print("Starting Multi-Phase Ingestion Pipeline...")
    cache = load_cache()
    conn = sqlite3.connect(DB_PATH)
    
    processed_count = 0
    skipped_count = 0
    
    for root, _, files in os.walk(VAULT_DIR):
        for file in files:
            if file.endswith('.md'):
                filepath = os.path.join(root, file)
                file_hash = get_file_hash(filepath)
                
                # Phase 3: Hash Caching
                if filepath in cache and cache[filepath] == file_hash:
                    skipped_count += 1
                    continue
                    
                print(f"Processing {file}...")
                process_file(filepath, conn)
                
                cache[filepath] = file_hash
                save_cache(cache)
                processed_count += 1
                
    conn.close()
    print(f"Pipeline complete! Processed: {processed_count}, Skipped: {skipped_count}")

if __name__ == "__main__":
    run_pipeline()
