import sqlite3

conn = sqlite3.connect('lore_forge_world.db')
print([t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")])
