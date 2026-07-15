import sqlite3
import csv
import json
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lore_forge_world.db"))
AZGAAR_STATES_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "map_data", "Okasha States 2026-06-26-06-57.csv"))
AZGAAR_BURGS_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "map_data", "Okasha Burgs 2026-06-26-06-56.csv"))

# ==========================================
# THE LORE-TO-MAP TRANSLATION DICTIONARY
# ==========================================
LORE_MAPPING = {
    "states": {
        "3": "Ursine Hegemony",
        "21": "Hive Commonwealth",
        "16": "Canopy Clans",
        "10": "Iron Caldera",
        "23": "Avian Empire",
        "25": "Vaneer Concord",
        "26": "River Folk",
        "22": "Dusk Husk Commonwealth",
        "14": "Coastal Theocracy",
        "4": "Heartlands Federation"
    },
    "burgs": {
        "16": "The Iron Caldera",     # Ignixa
        "17": "Verdant Tangle Capital", # Whispilight
        "7": "Flower Valley Capital"    # Cam Tri
    }
}

def init_map_tables(cursor):
    """Creates the physical map tables in SQLite if they don't exist."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS azgaar_states (
            state_id INTEGER PRIMARY KEY,
            lore_name TEXT,
            azgaar_original_name TEXT,
            color TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS azgaar_burgs (
            burg_id INTEGER PRIMARY KEY,
            state_id INTEGER,
            lore_name TEXT,
            azgaar_original_name TEXT,
            population INTEGER,
            x_coord REAL,
            y_coord REAL,
            is_capital INTEGER
        )
    """)

def ingest_states(cursor):
    """Reads the Okasha States CSV and maps them to Lore Factions."""
    print("Ingesting Azgaar States...")
    with open(AZGAAR_STATES_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            state_id = row.get('Id')
            original_name = row.get('State')
            color = row.get('Color')
            
            # Skip invalid or 'Neutral' states (usually ID 0)
            if not state_id or state_id == '0':
                continue
                
            # Apply Lore Translation if it exists
            lore_name = LORE_MAPPING["states"].get(state_id, original_name)
            
            cursor.execute("""
                INSERT OR REPLACE INTO azgaar_states (state_id, lore_name, azgaar_original_name, color)
                VALUES (?, ?, ?, ?)
            """, (state_id, lore_name, original_name, color))

def ingest_burgs(cursor):
    """Reads the Okasha Burgs (Cities) CSV and maps them to Lore Locations."""
    print("Ingesting Azgaar Burgs...")
    with open(AZGAAR_BURGS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            burg_id = row.get('Id')
            state_id = row.get('State')
            original_name = row.get('Burg')
            
            # handle cases where population might be empty string
            pop_str = row.get('Population', '0')
            if not pop_str: pop_str = '0'
            pop = float(pop_str) * 1000 
            
            x = row.get('X')
            y = row.get('Y')
            is_capital = 1 if row.get('Capital') == '1' else 0
            
            if not burg_id:
                continue

            # Apply Lore Translation
            lore_name = LORE_MAPPING["burgs"].get(burg_id, original_name)
            
            cursor.execute("""
                INSERT OR REPLACE INTO azgaar_burgs (burg_id, state_id, lore_name, azgaar_original_name, population, x_coord, y_coord, is_capital)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (burg_id, state_id, lore_name, original_name, pop, x, y, is_capital))

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    init_map_tables(cursor)
    ingest_states(cursor)
    ingest_burgs(cursor)
    
    conn.commit()
    conn.close()
    print("Azgaar Map Data successfully fused with Lore Database!")

if __name__ == "__main__":
    main()
