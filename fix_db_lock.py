import os
import re

filepath = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\core\ai_worker.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix NoneType issue
old_json_parse = """                    dissected_data = json.loads(clean_resp)
                    if dissected_data.get("category") and dissected_data["category"] != "General":"""
new_json_parse = """                    dissected_data = json.loads(clean_resp)
                    if not dissected_data:
                        dissected_data = {}
                    if dissected_data.get("category") and dissected_data["category"] != "General":"""
content = content.replace(old_json_parse, new_json_parse)

# 2. Fix the dangling connection lock
# I will find the block starting at "conn = sqlite3.connect(self.db_path, timeout=15.0)" inside the loop
# and ensure conn is closed in a finally block, or simply close it in the except block before doing the offline fallback.

# Let's replace the whole except block:
old_except = """            except Exception as e:
                print(f"Skipping JSON entity extraction for {filename}: {e}")
                
                try:
                    category = "General"
                    conn = sqlite3.connect(self.db_path, timeout=15.0)
                    conn.execute("PRAGMA journal_mode=WAL;")
                    cursor = conn.cursor()
                    cursor.execute(\"\"\"
                        INSERT INTO notes (title, content, category)
                        VALUES (?, ?, ?)
                        ON CONFLICT(title) DO UPDATE SET content=excluded.content, category=excluded.category
                    \"\"\", (os.path.splitext(filename)[0], raw_prose, category))
                    conn.commit()
                    conn.close()"""

new_except = """            except Exception as e:
                print(f"Skipping JSON entity extraction for {filename}: {e}")
                # Ensure the primary connection is closed so we don't lock the database forever
                try:
                    if 'conn' in locals():
                        conn.close()
                except Exception:
                    pass
                
                try:
                    category = "General"
                    conn2 = sqlite3.connect(self.db_path, timeout=15.0)
                    conn2.execute("PRAGMA journal_mode=WAL;")
                    cursor2 = conn2.cursor()
                    cursor2.execute(\"\"\"
                        INSERT INTO notes (title, content, category)
                        VALUES (?, ?, ?)
                        ON CONFLICT(title) DO UPDATE SET content=excluded.content, category=excluded.category
                    \"\"\", (os.path.splitext(filename)[0], raw_prose, category))
                    conn2.commit()
                    conn2.close()"""

content = content.replace(old_except, new_except)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Bugfix applied to ai_worker.py")
