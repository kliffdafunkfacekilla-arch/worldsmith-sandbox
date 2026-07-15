import sqlite3
import os

def fix_migration():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lore_forge_world.db"))
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables_to_migrate = [
        ('factions_old', 'factions'),
        ('actors_old', 'actors'),
        ('magic_layers_old', 'magic_layers')
    ]

    for old_table, new_table in tables_to_migrate:
        # Check if old_table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (old_table,))
        if not cursor.fetchone():
            print(f"{old_table} does not exist, skipping.")
            continue
            
        print(f"Migrating {old_table} to {new_table}...")

        # Ensure new table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (new_table,))
        if not cursor.fetchone():
            print(f"Error: target table {new_table} does not exist!")
            continue

        # Get columns of old table
        cursor.execute(f"PRAGMA table_info({old_table})")
        old_cols = [row[1] for row in cursor.fetchall()]

        # Get columns of new table
        cursor.execute(f"PRAGMA table_info({new_table})")
        new_cols = [row[1] for row in cursor.fetchall()]

        # Find intersecting columns
        common_cols = [col for col in old_cols if col in new_cols]
        
        if not common_cols:
            print(f"No common columns found between {old_table} and {new_table}. Skipping.")
            continue

        col_str = ", ".join(common_cols)
        
        # We might have partially inserted data if it crashed midway, so we can ignore conflicts or clear target table
        # Since this is a fresh migration run for the new schema, we'll clear the new table first to avoid dupes
        cursor.execute(f"DELETE FROM {new_table}")
        
        query = f"INSERT INTO {new_table} ({col_str}) SELECT {col_str} FROM {old_table}"
        print(f"Executing: {query}")
        cursor.execute(query)
        
        cursor.execute(f"DROP TABLE {old_table}")
        print(f"Successfully migrated {old_table} and dropped it.")

    conn.commit()
    conn.close()
    print("Migration fix complete!")

if __name__ == "__main__":
    fix_migration()
