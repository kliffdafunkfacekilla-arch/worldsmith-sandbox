import os

filepath = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\core\export_engine.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_tables = """            # The exact tables the story simulation needs to govern logic and space
            tables_to_export = [
                "factions", "cultures", "religions", "burgs", 
                "provinces", "calendar_config", "moons", "cells"
            ]"""
new_tables = """            # The exact tables the story simulation needs to govern logic and space
            tables_to_export = [
                "factions", "cultures", "religions", "burgs", 
                "provinces", "calendar_config", "moons", "cells",
                "actors", "faction_relations", "faction_economics"
            ]"""

if old_tables in content:
    content = content.replace(old_tables, new_tables)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("export_engine updated.")
