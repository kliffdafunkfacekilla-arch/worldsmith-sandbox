import os

filepath = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace factions table
old_factions = "cursor.execute(\"CREATE TABLE IF NOT EXISTS factions (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, color TEXT NOT NULL, gov_type TEXT DEFAULT 'Feudal Monarchy', dominant_cultures TEXT, dominant_religions TEXT, leaders TEXT, imports TEXT, exports TEXT, aggression_scale INTEGER DEFAULT 5, trade_scale INTEGER DEFAULT 5, explore_scale INTEGER DEFAULT 5, espionage_scale INTEGER DEFAULT 5, morale INTEGER DEFAULT 5, crime INTEGER DEFAULT 5, poverty INTEGER DEFAULT 5, freedom INTEGER DEFAULT 5, magic_stance TEXT DEFAULT 'Regulated', domain_type TEXT DEFAULT 'Both', treasury REAL DEFAULT 1000.0, capital_cell INTEGER, associated_note_id INTEGER, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)\")"
new_factions = "cursor.execute(\"CREATE TABLE IF NOT EXISTS factions (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, color TEXT NOT NULL, gov_type TEXT DEFAULT 'Feudal Monarchy', dominant_cultures TEXT, dominant_religions TEXT, aggression_scale INTEGER DEFAULT 5, trade_scale INTEGER DEFAULT 5, explore_scale INTEGER DEFAULT 5, espionage_scale INTEGER DEFAULT 5, morale INTEGER DEFAULT 5, crime INTEGER DEFAULT 5, poverty INTEGER DEFAULT 5, freedom INTEGER DEFAULT 5, magic_stance TEXT DEFAULT 'Regulated', domain_type TEXT DEFAULT 'Both', treasury REAL DEFAULT 1000.0, capital_cell INTEGER, associated_note_id INTEGER, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)\")"
content = content.replace(old_factions, new_factions)

# Replace settlements table
old_settlements = "cursor.execute(\"CREATE TABLE IF NOT EXISTS settlements (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, population REAL DEFAULT 10.0, cell_idx INTEGER, faction_id INTEGER, culture_id INTEGER, has_port INTEGER DEFAULT 0, has_university INTEGER DEFAULT 0, notable_locations TEXT, notable_persons_links TEXT, leaders_links TEXT, associated_note_id INTEGER, FOREIGN KEY(faction_id) REFERENCES factions(id) ON DELETE SET NULL, FOREIGN KEY(culture_id) REFERENCES cultures(id) ON DELETE SET NULL, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)\")"
new_settlements = "cursor.execute(\"CREATE TABLE IF NOT EXISTS settlements (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, population REAL DEFAULT 10.0, cell_idx INTEGER, faction_id INTEGER, culture_id INTEGER, has_port INTEGER DEFAULT 0, has_university INTEGER DEFAULT 0, notable_locations TEXT, leaders_links TEXT, associated_note_id INTEGER, FOREIGN KEY(faction_id) REFERENCES factions(id) ON DELETE SET NULL, FOREIGN KEY(culture_id) REFERENCES cultures(id) ON DELETE SET NULL, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)\")"
content = content.replace(old_settlements, new_settlements)

# Add new tables before the inconsistencies table
old_incon = '        cursor.execute("CREATE TABLE IF NOT EXISTS inconsistencies (id INTEGER PRIMARY KEY AUTOINCREMENT, subject_type TEXT, subject_id INTEGER, description TEXT, status TEXT DEFAULT \'Active\')")'
new_tables = """        cursor.execute("CREATE TABLE IF NOT EXISTS actors (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, faction_id INTEGER, current_cell_idx INTEGER, is_alive INTEGER DEFAULT 1, role TEXT, FOREIGN KEY(faction_id) REFERENCES factions(id))")
        cursor.execute("CREATE TABLE IF NOT EXISTS faction_relations (faction_a_id INTEGER, faction_b_id INTEGER, diplomacy_score INTEGER, treaty_status TEXT, UNIQUE(faction_a_id, faction_b_id), FOREIGN KEY(faction_a_id) REFERENCES factions(id), FOREIGN KEY(faction_b_id) REFERENCES factions(id))")
        cursor.execute("CREATE TABLE IF NOT EXISTS faction_economics (id INTEGER PRIMARY KEY AUTOINCREMENT, faction_id INTEGER, good_name TEXT, status TEXT, urgency_multiplier REAL, FOREIGN KEY(faction_id) REFERENCES factions(id))")
        cursor.execute("CREATE TABLE IF NOT EXISTS inconsistencies (id INTEGER PRIMARY KEY AUTOINCREMENT, subject_type TEXT, subject_id INTEGER, description TEXT, status TEXT DEFAULT 'Active')")"""
content = content.replace(old_incon, new_tables)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Main schema refactor complete.")
