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

    # 5. Factions / Sovereign States Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS factions (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            color TEXT,
            treasury REAL,
            tech_level INTEGER
        )
    """)

    # Actors Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            faction_id INTEGER,
            current_cell_idx INTEGER,
            is_alive BOOLEAN DEFAULT 1,
            role TEXT,
            FOREIGN KEY(faction_id) REFERENCES factions(id)
        )
    """)

    # Diplomacy Matrix
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faction_relations (
            faction_a_id INTEGER,
            faction_b_id INTEGER,
            diplomacy_score INTEGER,
            treaty_status TEXT,
            UNIQUE(faction_a_id, faction_b_id),
            FOREIGN KEY(faction_a_id) REFERENCES factions(id),
            FOREIGN KEY(faction_b_id) REFERENCES factions(id)
        )
    """)

    # Faction Economics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faction_economics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faction_id INTEGER,
            good_name TEXT,
            status TEXT,
            urgency_multiplier REAL,
            FOREIGN KEY(faction_id) REFERENCES factions(id)
        )
    """)

    # 6. Settlements Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settlements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            q INTEGER,
            r INTEGER,
            population INTEGER,
            faction_id INTEGER,
            FOREIGN KEY(faction_id) REFERENCES factions(id)
        )
    """)

    # 7. The Unbound Magic Layers Map (Using Plural name for consistency)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS magic_layers (
            cell_idx INTEGER PRIMARY KEY,
            magic_type TEXT NOT NULL,          -- 'Wild Magic', 'Abyssal Corruption', etc.
            ley_line_density REAL DEFAULT 0.0, -- Power metric scale
            flux_frequency REAL DEFAULT 1.0,   -- Interacts with calendar changes
            FOREIGN KEY(cell_idx) REFERENCES cells(id) ON DELETE CASCADE
        )
    """)

    # 8. Cosmic Records Archive
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS world_cosmology (
            day_index INTEGER PRIMARY KEY,
            season TEXT NOT NULL,
            active_constellation TEXT,
            magic_multiplier REAL DEFAULT 1.0  -- e.g., Wild magic areas surge when "The Mage Node" aligns
        )
    """)

    # 9. Inconsistencies Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inconsistencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 10. Customizable templates table
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
