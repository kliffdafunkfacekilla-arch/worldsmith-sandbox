import sqlite3
import os

def init_database():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lore_forge_world.db"))
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Notes Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            category TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 2. Assets/Tags Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    
    # 3. Redefined Voronoi Cells (Replaces old hex mapping)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cells (
            id INTEGER PRIMARY KEY,
            centroid_x REAL,
            centroid_y REAL,
            elevation REAL DEFAULT 0.0,
            moisture REAL DEFAULT 0.0,
            temperature REAL DEFAULT 0.0,
            biome TEXT,
            state_id INTEGER,
            province_id INTEGER,
            religion_id INTEGER,
            culture_id INTEGER,
            river_id INTEGER DEFAULT 0,
            flow_accumulation REAL DEFAULT 0.0
        )
    """)

    # 4. Cell Adjacency Matrix (Crucial for Azgaar expansion paths)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cell_neighbors (
            cell_id INTEGER,
            neighbor_id INTEGER,
            PRIMARY KEY (cell_id, neighbor_id)
        )
    """)

    # 5. The Unbound Magic Layer Map
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS magic_layer (
            cell_id INTEGER PRIMARY KEY,
            magic_type TEXT NOT NULL,          -- 'Wild Magic', 'Abyssal Corruption', etc.
            ley_line_density REAL DEFAULT 0.0, -- Power metric scale
            flux_frequency REAL DEFAULT 1.0,   -- Interacts with calendar changes
            FOREIGN KEY(cell_id) REFERENCES cells(id) ON DELETE CASCADE
        )
    """)

    # 6. Cosmic Records Archive
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS world_cosmology (
            day_index INTEGER PRIMARY KEY,
            season TEXT NOT NULL,
            active_constellation TEXT,
            magic_multiplier REAL DEFAULT 1.0  -- e.g., Wild magic areas surge when "The Mage Node" aligns
        )
    """)

    # 7. Inconsistencies Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inconsistencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 8. Customizable templates table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS world_templates (
            category TEXT PRIMARY KEY,
            fields_json TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_database()
