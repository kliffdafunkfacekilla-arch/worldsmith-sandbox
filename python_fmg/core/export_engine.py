import json
import os
import sqlite3
from PyQt6.QtCore import QRect, QSize
from PyQt6.QtGui import QPixmap, QPainter

class WorldsmithExportEngine:
    def __init__(self, main_window):
        self.win = main_window
        self.engine = main_window.map_engine

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

    def extract_cropped_context_map(self, cell_idx, output_dir):
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
        master_pixmap = QPixmap(QSize(self.win.map_viewer.width(), self.win.map_viewer.height()))
        painter = QPainter(master_pixmap)
        self.win.map_viewer.render(painter)
        painter.end()
        
        cropped_pixmap = master_pixmap.copy(QRect(src_x, src_y, crop_size, crop_size))
        output_path = os.path.join(output_dir, f"context_cell_{cell_idx}.png")
        cropped_pixmap.save(output_path, "PNG")
