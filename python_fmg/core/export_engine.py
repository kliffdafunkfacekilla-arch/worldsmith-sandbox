import json
import os
import sqlite3
from PyQt6.QtCore import QRect, QSize
from PyQt6.QtGui import QPixmap, QPainter

class WorldsmithExportEngine:
    def __init__(self, map_engine, db_path="lore_forge_world.db"):
        self.engine = map_engine
        self.db_path = db_path

    def compile_geojson_framework(self, output_path):
        """
        Translates all internal cell points, political borders, 
        and custom smuggling polylines into an industry-standard spatial GIS document.
        """
        geojson = {
            "type": "FeatureCollection",
            "features": []
        }

        # Export settlement nodes natively as geographic spatial points
        for burg in self.engine.burgs:
            cell = self.engine.cells[burg["cell_idx"]]
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(cell["x"]), float(cell["y"])]
                },
                "properties": {
                    "name": burg["name"],
                    "population": burg.get("population", 0),
                    "layer_z": cell.get("layer_z", "surface")
                }
            }
            geojson["features"].append(feature)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(geojson, f, indent=2)

    def extract_cropped_context_map(self, cell_idx, output_dir, map_viewer):
        """
        Captures a high-resolution sub-map square viewport centered exactly on a specific cell.
        Saves the cropped png inside the note folder for automated local wiki embedding.
        """
        cell = self.engine.cells[cell_idx]
        crop_size = 256
        
        # Calculate target bounding box limits around target pin coordinates
        src_x = int(cell["x"] - (crop_size / 2))
        src_y = int(cell["y"] - (crop_size / 2))
        
        # Instantiate flat output canvas texture grabber
        master_pixmap = QPixmap(QSize(map_viewer.width(), map_viewer.height()))
        painter = QPainter(master_pixmap)
        map_viewer.render(painter)
        painter.end()
        
        cropped_pixmap = master_pixmap.copy(QRect(src_x, src_y, crop_size, crop_size))
        output_path = os.path.join(output_dir, f"context_cell_{cell_idx}.png")
        cropped_pixmap.save(output_path, "PNG")

    def export_simulation_seed(self, output_path, db_path="lore_forge_world.db"):
        """
        Dumps all relational lore, rules, and spatial data from the SQLite database
        into a single JSON 'World Seed' for the external simulation app.
        """
        import sqlite3
        import json
        
        world_seed = {}
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row 
            cursor = conn.cursor()
            
            # The exact tables the story simulation needs to govern logic and space
            tables_to_export = [
                "factions", "cultures", "religions", "burgs", 
                "provinces", "calendar_config", "moons", "cells",
                "actors", "faction_relations", "faction_economics"
            ]
            
            for table in tables_to_export:
                cursor.execute(f"SELECT count(name) FROM sqlite_master WHERE type='table' AND name='{table}'")
                if cursor.fetchone()[0] == 1:
                    cursor.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()
                    world_seed[table] = [dict(row) for row in rows]
                else:
                    world_seed[table] = [] 
                    
            conn.close()
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(world_seed, f, indent=2)
                
            print(f"SUCCESS: Simulation seed exported to {output_path}")
            
        except sqlite3.Error as e:
            print(f"Database error during simulation export: {e}")
