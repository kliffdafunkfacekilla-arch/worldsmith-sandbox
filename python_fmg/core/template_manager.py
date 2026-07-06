import os
import sys
import sqlite3
import json

class TemplateManager:
    """
    Manages custom templates for the AI's worldbuilder checklist.
    Allows editing, adding new categories, and customizing layers/factions parameters.
    """
    def __init__(self, db_path="lore_forge_world.db"):
        self.db_path = db_path
        self.setup_templates_table()

    def setup_templates_table(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS world_templates (
                    category TEXT PRIMARY KEY,
                    fields_json TEXT NOT NULL
                )
            """)
            
            # Populate default customizable templates
            default_templates = {
                "Elevation (Map Layer)": ["Altitude Range", "Volcanic Activity", "Coastal Features"],
                "Biomes (Map Layer)": ["Climate Zones", "Vegetation Types", "Nutrient Vectors"],
                "Political States": ["Expansionism Rate", "Government Form", "Inhabitant Species (Beast-folk, Human, etc.)"],
                "Provinces": ["Local Governors", "Taxation Rate", "Resources"],
                "Religions": ["Deity Names", "Worship Style", "Holy Sites"],
                "Cultures": ["Language Name", "Namebases", "Architecture Style"],
                "Burgs": ["Trade Focus", "Population Cap", "City Map Layout"],
                "Magic Layer": ["Magic Types", "Power Level", "Ley Line Density"],
                "Technology": ["Tech Era", "Core Inventions", "Resource Dependencies"]
            }
            
            for cat, fields in default_templates.items():
                cursor.execute("""
                    INSERT OR IGNORE INTO world_templates (category, fields_json)
                    VALUES (?, ?)
                """, (cat, json.dumps(fields)))
                
            conn.commit()
            conn.close()
        except:
            pass

    def get_all_templates(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT category, fields_json FROM world_templates")
            rows = cursor.fetchall()
            conn.close()
            return {row[0]: json.loads(row[1]) for row in rows}
        except:
            return {}

    def save_template(self, category, fields):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO world_templates (category, fields_json)
                VALUES (?, ?)
            """, (category, json.dumps(fields)))
            conn.commit()
            conn.close()
        except:
            pass
