import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "lore_forge_world.db"))
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Setting up FTS5 Virtual Table...")
cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(title, content, category, content=notes, content_rowid=id)")

# Create triggers
print("Setting up Triggers...")
cursor.execute("""
CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, title, content, category) VALUES (new.id, new.title, new.content, new.category);
END;
""")
cursor.execute("""
CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, content, category) VALUES('delete', old.id, old.title, old.content, old.category);
END;
""")
cursor.execute("""
CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, content, category) VALUES('delete', old.id, old.title, old.content, old.category);
    INSERT INTO notes_fts(rowid, title, content, category) VALUES (new.id, new.title, new.content, new.category);
END;
""")

# Rebuild FTS
print("Rebuilding FTS index from existing notes...")
cursor.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")

conn.commit()
conn.close()
print("FTS5 Setup Complete.")
