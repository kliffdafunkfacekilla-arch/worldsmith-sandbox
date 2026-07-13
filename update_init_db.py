import os

filepath = r'c:\Users\krazy\Desktop\worldsmith-sandbox\scripts\init_database.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace factions table
old_factions = """    # 5. Factions / Sovereign States Table
    cursor.execute(\"\"\"
        CREATE TABLE IF NOT EXISTS factions (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            color TEXT,
            treasury REAL,
            tech_level INTEGER
        )
    \"\"\")"""

# It doesn't have imports/exports or leaders to remove anyway, but we'll leave it as is.
# Wait, let me add the new tables right after factions

new_tables = """    # 5. Factions / Sovereign States Table
    cursor.execute(\"\"\"
        CREATE TABLE IF NOT EXISTS factions (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            color TEXT,
            treasury REAL,
            tech_level INTEGER
        )
    \"\"\")

    # Actors Table
    cursor.execute(\"\"\"
        CREATE TABLE IF NOT EXISTS actors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            faction_id INTEGER,
            current_cell_idx INTEGER,
            is_alive BOOLEAN DEFAULT 1,
            role TEXT,
            FOREIGN KEY(faction_id) REFERENCES factions(id)
        )
    \"\"\")

    # Diplomacy Matrix
    cursor.execute(\"\"\"
        CREATE TABLE IF NOT EXISTS faction_relations (
            faction_a_id INTEGER,
            faction_b_id INTEGER,
            diplomacy_score INTEGER,
            treaty_status TEXT,
            UNIQUE(faction_a_id, faction_b_id),
            FOREIGN KEY(faction_a_id) REFERENCES factions(id),
            FOREIGN KEY(faction_b_id) REFERENCES factions(id)
        )
    \"\"\")

    # Faction Economics
    cursor.execute(\"\"\"
        CREATE TABLE IF NOT EXISTS faction_economics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faction_id INTEGER,
            good_name TEXT,
            status TEXT,
            urgency_multiplier REAL,
            FOREIGN KEY(faction_id) REFERENCES factions(id)
        )
    \"\"\")"""

content = content.replace(old_factions, new_tables)

# For settlements we just leave it since it doesn't have notable_persons_links either in init_database.py.

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("init_database schema refactor complete.")
