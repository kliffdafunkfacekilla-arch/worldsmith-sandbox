import os
import sqlite3

def init_db(db_path="lore_forge_world.db"):
    # Clean recreate
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Notes Table (Obsidian-Style)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT UNIQUE NOT NULL,
        content TEXT NOT NULL,
        category TEXT DEFAULT 'unclassified',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 2. Assets Table (Linking images/drawings to notes)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id INTEGER,
        file_path TEXT NOT NULL,
        description TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE
    )
    """)
    
    # 3. Tags Table (Obsidian tag support)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS note_tags (
        note_id INTEGER,
        tag_id INTEGER,
        PRIMARY KEY (note_id, tag_id),
        FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE,
        FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
    )
    """)
    
    # 4. Map Coordinates & Hexes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hexes (
        q INTEGER,
        r INTEGER,
        elevation REAL DEFAULT 0.0,
        biome TEXT,
        faction_id INTEGER,
        moisture REAL DEFAULT 0.0,
        temperature REAL DEFAULT 0.0,
        PRIMARY KEY (q, r)
    )
    """)
    
    # 5. Factions & States
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS factions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        treasury REAL DEFAULT 0.0,
        tech_level INTEGER DEFAULT 1,
        color TEXT DEFAULT '#ffffff'
    )
    """)
    
    # 6. Settlements & Burgs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settlements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        q INTEGER,
        r INTEGER,
        population INTEGER DEFAULT 1000,
        faction_id INTEGER,
        FOREIGN KEY(faction_id) REFERENCES factions(id) ON DELETE SET NULL,
        FOREIGN KEY(q, r) REFERENCES hexes(q, r) ON DELETE SET NULL
    )
    """)
    
    # 7. AI Inconsistencies & Prompts Log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inconsistencies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_type TEXT NOT NULL, -- 'note' or 'map'
        source_id TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'open', -- 'open', 'resolved', 'ignored'
        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()
    print("[+] SQLite Database clean schema initialized successfully.")

if __name__ == "__main__":
    init_db()
