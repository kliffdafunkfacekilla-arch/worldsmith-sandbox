import sqlite3
import argparse

def search_notes(query):
    conn = sqlite3.connect("lore_forge_world.db")
    cursor = conn.cursor()
    
    print(f"\\n--- Searching Lore Vault for: '{query}' ---")
    cursor.execute("""
        SELECT title, snippet(notes_fts, -1, '>>', '<<', '...', 64) 
        FROM notes_fts 
        WHERE notes_fts MATCH ? 
        ORDER BY rank LIMIT 10
    """, (query,))
    
    results = cursor.fetchall()
    if not results:
        print("No matches found.")
    
    for title, snippet in results:
        print(f"\\n[{title}]")
        print(f"  {snippet}")
        
    print("\\n--- Extracted Entities & Relationships ---")
    cursor.execute("""
        SELECT subject, relationship, target, context 
        FROM atomic_facts 
        WHERE subject LIKE ? OR target LIKE ?
        LIMIT 10
    """, (f"%{query}%", f"%{query}%"))
    
    facts = cursor.fetchall()
    if not facts:
        print("No structured relationships found.")
    for f in facts:
        print(f"  {f[0]} -> {f[1]} -> {f[2]} ({f[3]})")
        
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query your Worldbuilding Knowledge Graph")
    parser.add_argument("query", type=str, help="The term or entity to search for")
    args = parser.parse_args()
    
    search_notes(args.query)
