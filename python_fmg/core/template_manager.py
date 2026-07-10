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
                "History-Timeline": ["Era", "Major Events", "Key Figures"],
                "Cosmology": ["Origin Myth", "Physical Laws", "Planes of Existence"],
                "Magic-Powers": ["Rules", "Sources", "Limitations"],
                "Tech": ["Tech Era", "Core Inventions", "Resource Dependencies"],
                "Cultures": ["Traditions", "Values", "Taboos"],
                "Kingdoms-Empires-Countries": ["Government", "Demographics", "Territory"],
                "Factions-Organizations": ["Purpose", "Hierarchy", "Influence"],
                "Species": ["Biology", "Lifespan", "Habitats"],
                "Locations": ["Climate", "Geography", "Points of Interest"],
                "People": ["Appearance", "Personality", "Background"],
                "Religions": ["Deities", "Dogma", "Practices"],
                "Items-Objects": ["Appearance", "Function", "History"],
                "Flora": ["Environment", "Uses", "Hazards"],
                "Fauna": ["Diet", "Behavior", "Abilities"],
                "Economy": ["Currency", "Major Exports", "Wealth Distribution"],
                "Ecology": ["Biomes", "Food Chains", "Climate Trends"],
                "Meta": ["Themes", "Tropes", "Inspirations"]
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
