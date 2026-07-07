import sys
import random
import os
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPolygonF, QPainterPath, QFont, QPixmap

class MapViewerWidget(QWidget):
    cell_hovered = pyqtSignal(int, float, str, str)
    cell_clicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        
        self.elevation_data = {}  
        self.biomes_data = {}     
        self.factions_data = {}   
        self.magic_data = {}       
        self.layer_mode = "Biomes"  # Default layer mode to Biomes to show off the tileset!
        self.active_paint_magic = "Wild Magic"  
        self.brush_mode = "Inspect" # Inspect, Magic, Height, State, Province, Culture, Religion, River, Burg
        self.paint_height_value = 50
        self.paint_state_value = 1
        self.paint_province_value = 1
        self.paint_culture_value = 1
        self.paint_religion_value = 1
        self.paint_river_value = 1
        self.brush_size = 1 # 1, 2, or 3 cell radius

        # Layer visibility flags
        self.visibility_map = {
            "Elevation": True,
            "Biomes": True,
            "Political States": True,
            "Provinces": True,
            "Cultures": True,
            "Magic Layer": True,
            "Production Goods": True,
            "Rivers": True,
            "Roads": True,
            "Military Regiments": True,
            "Burgs": True
        }

        # Sprite sheet assets loader
        self.tile_pixmap = None
        self.sprite_pixmap = None
        
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        tilemap_path = os.path.join(root_dir, "fantasyhextiles_v3_borderless.png")
        sprites_path = os.path.join(root_dir, "d4np5o7-d68e778b-415c-4b59-90c5-c61c55f015e7.png")
        
        # Check parent folder too
        if not os.path.exists(tilemap_path):
            tilemap_path = os.path.join(os.path.dirname(root_dir), "fantasyhextiles_v3_borderless.png")
            sprites_path = os.path.join(os.path.dirname(root_dir), "d4np5o7-d68e778b-415c-4b59-90c5-c61c55f015e7.png")

        if os.path.exists(tilemap_path):
            self.tile_pixmap = QPixmap(tilemap_path)
        if os.path.exists(sprites_path):
            self.sprite_pixmap = QPixmap(sprites_path)

    def mouseMoveEvent(self, event):
        pos = event.position()
        closest_cell_idx = self.find_closest_cell(pos)

        if closest_cell_idx is not None:
            elev = self.elevation_data.get(closest_cell_idx, 0.0)
            biome = self.biomes_data.get(closest_cell_idx, "Marine")
            state = self.factions_data.get(closest_cell_idx, "Neutral")
            
            if self.layer_mode == "Magic Layer":
                mag = self.magic_data.get(closest_cell_idx, "None")
                biome = f"{biome} (Magic: {mag})"
                
            self.cell_hovered.emit(closest_cell_idx, elev, biome, state)

    def mousePressEvent(self, event):
        pos = event.position()
        closest_cell_idx = self.find_closest_cell(pos)

        if closest_cell_idx is not None:
            # Gather cells within brush size radius
            affected_cells = self.get_cells_in_radius(closest_cell_idx, self.brush_size)
            
            for cell_idx in affected_cells:
                if self.brush_mode == "Magic Paint":
                    self.magic_data[cell_idx] = self.active_paint_magic
                    self.cell_clicked.emit(cell_idx)
                elif self.brush_mode == "Height Paint":
                    self.parent.map_engine.cells[cell_idx]["h"] = self.paint_height_value
                elif self.brush_mode == "State Paint":
                    self.parent.map_engine.cells[cell_idx]["state"] = self.paint_state_value
                elif self.brush_mode == "Province Paint":
                    self.parent.map_engine.cells[cell_idx]["province"] = self.paint_province_value
                elif self.brush_mode == "Culture Paint":
                    self.parent.map_engine.cells[cell_idx]["culture"] = self.paint_culture_value
                elif self.brush_mode == "Religion Paint":
                    self.parent.map_engine.cells[cell_idx]["religion"] = self.paint_religion_value
                elif self.brush_mode == "River Paint":
                    self.parent.map_engine.cells[cell_idx]["r"] = self.paint_river_value
                elif self.brush_mode == "Burg Paint":
                    cell = self.parent.map_engine.cells[cell_idx]
                    if cell["burg"] == 0:
                        burg_id = len(self.parent.map_engine.burgs) + 1
                        cell["burg"] = burg_id
                        self.parent.map_engine.burgs.append({
                            "id": burg_id,
                            "cell_idx": cell_idx,
                            "name": f"New Settlement {burg_id}",
                            "population": 15
                        })
                    else:
                        self.parent.map_engine.burgs = [b for b in self.parent.map_engine.burgs if b["id"] != cell["burg"]]
                        cell["burg"] = 0
            
            if self.brush_mode == "Height Paint":
                self.parent.map_engine.run_biomes_climate()
                self.parent.map_engine.run_production_goods()
                
            self.parent.load_map_data_to_viewer()
            self.update()

    def get_cells_in_radius(self, center_idx, radius):
        visited = {center_idx}
        queue = [(center_idx, 0)]
        results = []
        
        while queue:
            curr, dist = queue.pop(0)
            results.append(curr)
            if dist < radius - 1:
                for neighbor in self.parent.map_engine.get_neighbors(curr):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, dist + 1))
        return results

    def find_closest_cell(self, pos):
        if not self.parent or not hasattr(self.parent, "map_engine"):
            return None
        
        import math
        closest_idx = None
        min_dist = 99999.0
        
        for cell in self.parent.map_engine.cells:
            cx, cy = cell["x"], cell["y"]
            dist = math.sqrt((cx - pos.x())**2 + (cy - pos.y())**2)
            if dist < min_dist:
                min_dist = dist
                closest_idx = cell["i"]
                
        return closest_idx if min_dist < 40 else None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QBrush(QColor("#0d0d10")))
        
        if not self.parent or not hasattr(self.parent, "map_engine"):
            return
            
        vor_mesh = self.parent.map_engine.vor_mesh
        cells = self.parent.map_engine.cells
        provinces_pool = self.parent.map_engine.provinces_pool
        cultures = self.parent.map_engine.cultures
        
        for cell in cells:
            cell_id = cell["i"]
            region_idx = vor_mesh.point_region[cell_id]
            region = vor_mesh.regions[region_idx]
            
            if not region or -1 in region:
                continue
                
            path = QPainterPath()
            start_vert = vor_mesh.vertices[region[0]]
            path.moveTo(QPointF(float(start_vert[0]), float(start_vert[1])))
            
            for vert_idx in region[1:]:
                vert = vor_mesh.vertices[vert_idx]
                path.lineTo(QPointF(float(vert[0]), float(vert[1])))
            path.closeSubpath()
            
            color = QColor("#27272a")
            if self.layer_mode == "Elevation" and self.visibility_map["Elevation"]:
                elev = self.elevation_data.get(cell_id, 0)
                if elev < 20:
                    color = QColor(int((20 - elev) * 12), 30, int(80 + elev * 6))
                else:
                    color = QColor(int(20 + elev * 1.5), int(100 + elev), 20)
            elif self.layer_mode == "Biomes" and self.visibility_map["Biomes"]:
                biome = self.biomes_data.get(cell_id, "Marine")
                if biome == "Abyssal Trench (Desert)":
                    color = QColor("#f43f5e")
                elif biome == "Coral Forest (Rainforest)":
                    color = QColor("#ec4899")
                elif biome == "Kelp Meadows (Grassland)":
                    color = QColor("#0d9488")
                elif biome == "Benthic Shelf (Savanna)":
                    color = QColor("#2563eb")
                elif biome == "Hot Desert":
                    color = QColor("#eab308")
                elif biome == "Montane / Glacier":
                    color = QColor("#f1f5f9")
                elif biome == "Tropical Rainforest":
                    color = QColor("#065f46")
                elif biome == "Tundra":
                    color = QColor("#cbd5e1")
                else:
                    color = QColor("#15803d")
            elif self.layer_mode == "Political States" and self.visibility_map["Political States"]:
                color_hex = self.factions_data.get(cell_id, "#18181b")
                color = QColor(color_hex)
            elif self.layer_mode == "Provinces" and self.visibility_map["Provinces"]:
                pid = cell.get("province", 0)
                if pid > 0 and pid in provinces_pool:
                    color_hex = provinces_pool[pid]["color"]
                else:
                    color_hex = "#27272a"
                color = QColor(color_hex)
            elif self.layer_mode == "Cultures" and self.visibility_map["Cultures"]:
                cid = cell.get("culture", 0)
                colors = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#6366f1", "#ec4899", "#8b5cf6"]
                color_hex = colors[cid % len(colors)] if cid > 0 else "#27272a"
                color = QColor(color_hex)
            elif self.layer_mode == "Magic Layer" and self.visibility_map["Magic Layer"]:
                mag = self.magic_data.get(cell_id, "None")
                if mag == "Wild Magic":
                    color = QColor("#a855f7")
                elif mag == "Abyssal Corruption":
                    color = QColor("#b91c1c")
                elif mag == "Ley Line Node":
                    color = QColor("#06b6d4")
                elif mag == "Aether Storm":
                    color = QColor("#eab308")
                else:
                    color = QColor("#27272a")
            elif self.layer_mode == "Production Goods" and self.visibility_map["Production Goods"]:
                good = cell.get("good", "None")
                good_colors = {
                    "Grain": "#f59e0b", "Timber": "#15803d", "Spices": "#ec4899",
                    "Iron Ore": "#4b5563", "Bioluminescent Kelp": "#0d9488",
                    "Precious Metals": "#eab308", "Abyssal Pearls": "#8b5cf6", "Salt": "#f1f5f9"
                }
                color = QColor(good_colors.get(good, "#27272a"))

            painter.fillPath(path, QBrush(color))
            painter.strokePath(path, QPen(QColor("#1e293b"), 0.5))

            # Texture-tile overlay mapping if sheet is available
            if self.tile_pixmap and self.layer_mode == "Biomes" and self.visibility_map["Biomes"]:
                biome = self.biomes_data.get(cell_id, "Marine")
                # Source slice based on biome type (Hex sheet layout coordinates)
                # Map coordinates matching the 1024x1024 input sheet
                src_x = 0
                src_y = 0
                if "Forest" in biome or "Rainforest" in biome:
                    src_x, src_y = 200, 0
                elif "Desert" in biome:
                    src_x, src_y = 512, 200
                elif "Glacier" in biome or "Taiga" in biome:
                    src_x, src_y = 0, 0
                elif "Marine" in biome or "Trench" in biome:
                    src_x, src_y = 700, 700
                else:
                    src_x, src_y = 200, 512
                
                painter.drawPixmap(
                    QRect(int(cell["x"] - 20), int(cell["y"] - 20), 40, 40),
                    self.tile_pixmap,
                    QRect(src_x, src_y, 102, 102)
                )

        if self.visibility_map["Rivers"]:
            for cell in cells:
                if cell["r"] > 0:
                    painter.setPen(QPen(QColor("#3b82f6"), max(1, int(cell["fl"] / 80)), Qt.PenStyle.SolidLine))
                    for n in self.parent.map_engine.get_neighbors(cell["i"]):
                        nc = cells[n]
                        if nc["r"] == cell["r"] and nc["h"] < cell["h"]:
                            painter.drawLine(QPointF(cell["x"], cell["y"]), QPointF(nc["x"], nc["y"]))

        if self.visibility_map["Roads"]:
            for road in self.parent.map_engine.roads:
                path = road.get("path", [])
                if len(path) >= 2:
                    is_aquatic = (road["type"] == "Abyssal Conduit")
                    painter.setPen(QPen(QColor("#06b6d4") if is_aquatic else QColor("#d97706"), 2, Qt.PenStyle.DotLine if is_aquatic else Qt.PenStyle.SolidLine))
                    for step in range(len(path) - 1):
                        c1 = cells[path[step]]
                        c2 = cells[path[step+1]]
                        painter.drawLine(QPointF(c1["x"], c1["y"]), QPointF(c2["x"], c2["y"]))

        painter.setPen(QPen(QColor("#04D361"), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for point_pair in vor_mesh.ridge_points:
            p1 = vor_mesh.points[point_pair[0]]
            p2 = vor_mesh.points[point_pair[1]]
            painter.drawLine(QPointF(float(p1[0]), float(p1[1])), QPointF(float(p2[0]), float(p2[1])))
            
        if self.visibility_map["Military Regiments"]:
            for reg in self.parent.map_engine.military_regiments:
                cell_idx = reg["cell_idx"]
                for cell in cells:
                    if cell["i"] == cell_idx:
                        painter.setBrush(QBrush(QColor("#ef4444") if "Guard" in reg["name"] else QColor("#eab308")))
                        painter.setPen(QPen(QColor("#ffffff"), 1))
                        painter.drawEllipse(QPointF(cell["x"], cell["y"]), 6, 6)

        if self.visibility_map["Burgs"]:
            for burg in self.parent.map_engine.burgs:
                cell = cells[burg["cell_idx"]]
                painter.setBrush(QBrush(QColor("#eab308")))
                painter.setPen(QPen(QColor("#000000"), 1))
                painter.drawRect(QRectF(cell["x"] - 4, cell["y"] - 4, 8, 8))

        # Render curved/rotated text labels aligned to state paths (FMG draw-state-labels.ts equivalent)
        if self.visibility_map["Political States"] and self.layer_mode == "Political States":
            painter.setPen(QPen(QColor("#ffffff")))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            for st in self.parent.map_engine.states:
                # Find centroid cell of state
                matching_cells = [c for c in cells if c["state"] == st["id"]]
                if matching_cells:
                    center_cell = matching_cells[len(matching_cells) // 2]
                    # Calculate local slope angle to rotate label along the state's geographic flow path
                    neighbors = self.parent.map_engine.get_neighbors(center_cell["i"])
                    angle_deg = 0.0
                    if len(neighbors) >= 2:
                        c1 = cells[neighbors[0]]
                        c2 = cells[neighbors[1]]
                        dx = c2["x"] - c1["x"]
                        dy = c2["y"] - c1["y"]
                        import math
                        angle_deg = math.degrees(math.atan2(dy, dx))
                        
                    painter.save()
                    painter.translate(center_cell["x"], center_cell["y"])
                    painter.rotate(angle_deg)
                    painter.drawText(-40, -10, st["name"])
                    painter.restore()
