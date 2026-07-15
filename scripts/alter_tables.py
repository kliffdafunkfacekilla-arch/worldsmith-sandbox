import sqlite3
import os

def alter_tables():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lore_forge_world.db"))
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE actors ADD COLUMN historical_note TEXT")
        print("Added historical_note to actors.")
    except Exception as e: print("actors.historical_note:", e)

    try:
        cursor.execute("ALTER TABLE actors ADD COLUMN school_affinity TEXT")
        print("Added school_affinity to actors.")
    except Exception as e: print("actors.school_affinity:", e)
    
    try:
        cursor.execute("ALTER TABLE magic_layers ADD COLUMN name TEXT UNIQUE")
        print("Added name to magic_layers.")
    except Exception as e: print("magic_layers.name:", e)
    
    try:
        cursor.execute("ALTER TABLE magic_layers ADD COLUMN mode_type TEXT")
        print("Added mode_type to magic_layers.")
    except Exception as e: print("magic_layers.mode_type:", e)

    try:
        cursor.execute("ALTER TABLE magic_layers ADD COLUMN element TEXT")
        print("Added element to magic_layers.")
    except Exception as e: print("magic_layers.element:", e)
    
    try:
        cursor.execute("ALTER TABLE magic_layers ADD COLUMN effect_field_description TEXT")
        print("Added effect_field_description to magic_layers.")
    except Exception as e: print("magic_layers.effect_field_description:", e)
    
    try:
        cursor.execute("ALTER TABLE magic_layers ADD COLUMN original_magistar TEXT")
        print("Added original_magistar to magic_layers.")
    except Exception as e: print("magic_layers.original_magistar:", e)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    alter_tables()
