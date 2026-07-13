import os
import re

filepath = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add atomic_facts table creation
old_incon = '        cursor.execute("CREATE TABLE IF NOT EXISTS inconsistencies (id INTEGER PRIMARY KEY AUTOINCREMENT, subject_type TEXT, subject_id INTEGER, description TEXT, status TEXT DEFAULT \'Active\')")'
new_tables = """        cursor.execute("CREATE TABLE IF NOT EXISTS atomic_facts (id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT NOT NULL, relationship TEXT NOT NULL, target TEXT NOT NULL, context TEXT, associated_note_id INTEGER, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS inconsistencies (id INTEGER PRIMARY KEY AUTOINCREMENT, subject_type TEXT, subject_id INTEGER, description TEXT, status TEXT DEFAULT 'Active')")"""

if old_incon in content:
    content = content.replace(old_incon, new_tables)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("atomic_facts added to schema.")
