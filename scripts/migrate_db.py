import sqlite3
import os

def migrate():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lore_forge_world.db"))
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Starting migration...")

    # Factions
    print("Migrating factions...")
    cursor.execute("ALTER TABLE factions RENAME TO factions_old")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS factions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            status TEXT,
            color TEXT,
            treasury REAL,
            tech_level INTEGER
        )
    """)
    cursor.execute("""
        INSERT INTO factions (id, name, color, treasury, tech_level)
        SELECT id, name, color, treasury, tech_level FROM factions_old
    """)
    cursor.execute("DROP TABLE factions_old")

    # Actors
    print("Migrating actors...")
    cursor.execute("ALTER TABLE actors RENAME TO actors_old")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            faction_id INTEGER,
            current_cell_idx INTEGER,
            is_alive BOOLEAN DEFAULT 1,
            role TEXT,
            historical_note TEXT,
            school_affinity TEXT,
            FOREIGN KEY(faction_id) REFERENCES factions(id)
        )
    """)
    cursor.execute("""
        INSERT INTO actors (id, name, faction_id, current_cell_idx, is_alive, role)
        SELECT id, name, faction_id, current_cell_idx, is_alive, role FROM actors_old
    """)
    cursor.execute("DROP TABLE actors_old")

    # Magic Layers
    print("Migrating magic_layers...")
    cursor.execute("ALTER TABLE magic_layers RENAME TO magic_layers_old")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS magic_layers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            cell_idx INTEGER,
            magic_type TEXT,
            ley_line_density REAL DEFAULT 0.0,
            flux_frequency REAL DEFAULT 1.0,
            mode_type TEXT,
            element TEXT,
            effect_field_description TEXT,
            original_magistar TEXT,
            FOREIGN KEY(cell_idx) REFERENCES cells(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        INSERT INTO magic_layers (cell_idx, magic_type, ley_line_density, flux_frequency)
        SELECT cell_idx, magic_type, ley_line_density, flux_frequency FROM magic_layers_old
    """)
    cursor.execute("DROP TABLE magic_layers_old")

    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
