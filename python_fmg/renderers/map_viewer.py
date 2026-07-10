import sys
import random
import os
from PyQt6.QtWidgets import QWidget, QMessageBox
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
        self.paint_biome_value = "Hot Desert"
        self.paint_good_value = "Grain"
        self.brush_size = 1 # 1, 2, or 3 cell radius

        # Layer visibility flags
        self.visibility_map = {
            "Elevation": True,
            "Biomes": True,
            "Political States": True,
            "Provinces": True,
            "Cultures": True,
            "Religion": True,
            "Burgs": True,
            "Routes": True,
            "Rivers": True,
            "Roads": True,
            "Military Regiments": True,
            "Zones": True,
            "Temperature": True,
            "Precipitation": True,
            "Population Density": True,
            "Ice": True,
            "Coastlines": True,
            "Borders": True,
            "Relief Icons": True,
            "Markers": True,
            "Emblems": True,
            "Grid": True,
            "Coordinates": True,
            "Compass": True,
            "Scale Bar": True,
            "Vignette": True
        }

        # Zoom and Pan state
        self.zoom_factor = 1.0
        self.pan_offset = QPointF(0, 0)
        self.last_pan_pos = None

        # Sprite sheet assets loader
        self.tile_pixmap = None
        self.sprite_pixmap = None
        
        # We need to find the files in the workspace directory.
        # This resolves to c:/Users/krazy/Desktop/worldsmith-sandbox
        workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        tilemap_path = os.path.join(workspace_dir, "fantasyhextiles_v3_borderless.png")
        sprites_path = os.path.join(workspace_dir, "d4np5o7-d68e778b-415c-4b59-90c5-c61c55f015e7.png")
        
        if not os.path.exists(tilemap_path) or not os.path.exists(sprites_path):
            print(f"WARNING: Missing tilemap/sprites in {workspace_dir}!")
            # We'll use a delayed popup after window shows to ensure it renders correctly
            self._missing_assets = True
        else:
            self._missing_assets = False
            self.tile_pixmap = QPixmap(tilemap_path)
            self.sprite_pixmap = QPixmap(sprites_path)

    def screen_to_world(self, pos):
        return QPointF(
            (pos.x() - self.pan_offset.x()) / self.zoom_factor,
            (pos.y() - self.pan_offset.y()) / self.zoom_factor
        )

    def mouseMoveEvent(self, event):
        if self.last_pan_pos is not None:
            delta = event.position() - self.last_pan_pos
            self.pan_offset += delta
            self.last_pan_pos = event.position()
            self.update()
            return
            
        world_pos = self.screen_to_world(event.position())
        closest_cell_idx = self.find_closest_cell(world_pos)

        if closest_cell_idx is not None:
            elev = self.elevation_data.get(closest_cell_idx, 0.0)
            biome = self.biomes_data.get(closest_cell_idx, "Marine")
            state = self.factions_data.get(closest_cell_idx, "Neutral")
            
            if self.layer_mode == "Magic Layer":
                mag = self.magic_data.get(closest_cell_idx, "None")
                biome = f"{biome} (Magic: {mag})"
                
            self.cell_hovered.emit(closest_cell_idx, elev, biome, state)
            
            if event.buttons() & Qt.MouseButton.LeftButton:
                self.apply_brush_to_cell(closest_cell_idx)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or event.button() == Qt.MouseButton.RightButton:
            if self.brush_mode == "Road Paint" and event.button() == Qt.MouseButton.RightButton:
                pass # Let road drawing logic handle it
            else:
                self.last_pan_pos = event.position()
                return

        world_pos = self.screen_to_world(event.position())
        closest_cell_idx = self.find_closest_cell(world_pos)

        if event.button() == Qt.MouseButton.RightButton:
            if self.brush_mode == "Road Paint" and hasattr(self, "road_paint_active_path") and self.road_paint_active_path:
                if len(self.road_paint_active_path) > 1:
                    self.parent.map_engine.roads.append({
                        "id": len(self.parent.map_engine.roads) + 1,
                        "from_burg": 0, "to_burg": 0,
                        "path": self.road_paint_active_path,
                        "type": "Custom Road"
                    })
                self.road_paint_active_path = None
                self.parent.statusBar().showMessage("Road Paint: Road saved.")
                self.update()
            return

        if event.button() == Qt.MouseButton.LeftButton and closest_cell_idx is not None:
            self.cell_clicked.emit(closest_cell_idx)
            self.apply_brush_to_cell(closest_cell_idx)
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or event.button() == Qt.MouseButton.RightButton:
            self.last_pan_pos = None

    def wheelEvent(self, event):
        zoom_in = event.angleDelta().y() > 0
        old_zoom = self.zoom_factor
        
        if zoom_in:
            self.zoom_factor = min(15.0, self.zoom_factor * 1.15)
        else:
            self.zoom_factor = max(0.1, self.zoom_factor / 1.15)
            
        pos = event.position()
        self.pan_offset = pos - (pos - self.pan_offset) * (self.zoom_factor / old_zoom)
        self.update()

    def apply_brush_to_cell(self, closest_cell_idx):
        if self.brush_mode == "Road Paint":
            if not hasattr(self, "road_paint_active_path") or self.road_paint_active_path is None:
                self.road_paint_active_path = [closest_cell_idx]
                self.parent.statusBar().showMessage("Road Paint: Started. Click the next cell to draw the path. Right-click to finish.")
            else:
                last_cell = self.road_paint_active_path[-1]
                path_segment = self.parent.map_engine.find_astar_path(last_cell, closest_cell_idx)
                if path_segment:
                    self.road_paint_active_path.extend(path_segment[1:])
                self.parent.statusBar().showMessage("Road Paint: Path extended. Click next cell, or Right-click to finish.")
            self.update()
            return
            
        if self.brush_mode == "Road Delete":
            # Find any road containing this cell and remove it
            original_len = len(self.parent.map_engine.roads)
            self.parent.map_engine.roads = [r for r in self.parent.map_engine.roads if closest_cell_idx not in r.get("path", [])]
            if len(self.parent.map_engine.roads) < original_len:
                self.parent.statusBar().showMessage("Road deleted.")
            self.update()
            return

        if self.brush_mode == "Military Paint":
            state = self.parent.map_engine.cells[closest_cell_idx]["state"]
            if state > 0:
                # Remove existing if clicking on one, otherwise add
                existing = [r for r in self.parent.map_engine.military_regiments if r["cell_idx"] == closest_cell_idx]
                if existing:
                    self.parent.map_engine.military_regiments = [r for r in self.parent.map_engine.military_regiments if r["cell_idx"] != closest_cell_idx]
                    self.parent.statusBar().showMessage("Military Paint: Regiment removed.")
                else:
                    reg_id = max([r["id"] for r in self.parent.map_engine.military_regiments] + [0]) + 1
                    state_name = next((s["name"] for s in self.parent.map_engine.states if s["id"] == state), "Unknown")
                    self.parent.map_engine.military_regiments.append({
                        "id": reg_id,
                        "state_id": state,
                        "name": f"1st Army of {state_name}",
                        "cell_idx": closest_cell_idx,
                        "total_troops": 1000
                    })
                    self.parent.statusBar().showMessage("Military Paint: Regiment deployed.")
            else:
                self.parent.statusBar().showMessage("Military Paint: Cannot deploy troops on unowned land.")
            self.update()
            return
            
        if self.brush_mode == "Zone Paint":
            affected_cells = self.get_cells_in_radius(closest_cell_idx, self.brush_size)
            for cell_idx in affected_cells:
                self.parent.map_engine.cells[cell_idx]["zone"] = 1 if event.button() == Qt.MouseButton.LeftButton else 0
            self.update()
            return

        # Handle terraforming tools first
        if self.brush_mode in ["Height Raise", "Height Lower", "Height Smooth"]:
            self.parent.map_engine.apply_height_brush(closest_cell_idx, self.brush_size + 1, self.brush_mode, intensity=8)
            self.parent.load_map_data_to_viewer()
            self.update()
            return
            
        # Gather cells within brush size radius for standard painting
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
            elif self.brush_mode == "Biome Paint":
                self.parent.map_engine.cells[cell_idx]["biome"] = self.paint_biome_value
                self.biomes_data[cell_idx] = self.paint_biome_value
            elif self.brush_mode == "Production Paint":
                self.parent.map_engine.cells[cell_idx]["good"] = self.paint_good_value
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
        
        if self.brush_mode in ["Height Paint", "Height Raise", "Height Lower", "Height Smooth"]:
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
            
        painter.save()
        painter.translate(self.pan_offset)
        painter.scale(self.zoom_factor, self.zoom_factor)
        
        engine_width = self.parent.map_engine.width
        engine_height = self.parent.map_engine.height
        painter.setClipRect(QRectF(0, 0, engine_width, engine_height))
        
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
            elif self.layer_mode == "Temperature" and self.visibility_map["Temperature"]:
                temp = cell.get("temp", 15)
                # Map -20 to 40 C to blue -> red
                t = max(0, min(1, (temp + 20) / 60))
                color = QColor(int(t * 255), int((1 - abs(t - 0.5) * 2) * 200), int((1 - t) * 255))
            elif self.layer_mode == "Precipitation" and self.visibility_map["Precipitation"]:
                prec = cell.get("prec", 20)
                # Map 0 to 100 to brown -> green -> blue
                if prec < 30:
                    t = prec / 30
                    color = QColor(int(200 - t * 100), int(150 + t * 50), 50)
                else:
                    t = min(1, (prec - 30) / 70)
                    color = QColor(50, int(200 - t * 100), int(100 + t * 155))
            elif self.layer_mode == "Population Density" and self.visibility_map["Population Density"]:
                pop = cell.get("pop", 0)
                t = min(1, pop / 10.0) # Assume 10 is high density
                color = QColor(int(255 * t), 50, int(255 - 255 * t))
            elif self.layer_mode == "Ice" and self.visibility_map["Ice"]:
                temp = cell.get("temp", 15)
                if temp < -5:
                    color = QColor(240, 248, 255) # AliceBlue for deep ice
                elif temp < 0:
                    color = QColor(220, 230, 240)
                else:
                    color = QColor("#27272a") # Base ground

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
                    is_aquatic = (road.get("type") == "Abyssal Conduit")
                    painter.setPen(QPen(QColor("#06b6d4") if is_aquatic else QColor("#d97706"), 2, Qt.PenStyle.DotLine if is_aquatic else Qt.PenStyle.SolidLine))
                    for step in range(len(path) - 1):
                        c1 = cells[path[step]]
                        c2 = cells[path[step+1]]
                        painter.drawLine(QPointF(c1["x"], c1["y"]), QPointF(c2["x"], c2["y"]))

            # Render active road being painted
            if hasattr(self, "road_paint_active_path") and self.road_paint_active_path:
                painter.setPen(QPen(QColor("#f59e0b"), 3, Qt.PenStyle.DashLine))
                path = self.road_paint_active_path
                for step in range(len(path) - 1):
                    c1 = cells[path[step]]
                    c2 = cells[path[step+1]]
                    painter.drawLine(QPointF(c1["x"], c1["y"]), QPointF(c2["x"], c2["y"]))

        # Borders and Coastlines
        if self.visibility_map.get("Coastlines", True):
            painter.setPen(QPen(QColor("#000000"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for (p1_idx, p2_idx), v_indices in zip(vor_mesh.ridge_points, vor_mesh.ridge_vertices):
                if -1 in v_indices: continue
                if p1_idx >= len(cells) or p2_idx >= len(cells): continue
                c1 = cells[p1_idx]
                c2 = cells[p2_idx]
                # Coastline if one is marine (<20) and other is land (>=20)
                if (c1.get("h", 20) >= 20) != (c2.get("h", 20) >= 20):
                    v1 = vor_mesh.vertices[v_indices[0]]
                    v2 = vor_mesh.vertices[v_indices[1]]
                    painter.drawLine(QPointF(float(v1[0]), float(v1[1])), QPointF(float(v2[0]), float(v2[1])))

        if self.visibility_map.get("Borders", True):
            # Bold colored lines separating political states
            for (p1_idx, p2_idx), v_indices in zip(vor_mesh.ridge_points, vor_mesh.ridge_vertices):
                if -1 in v_indices: continue
                if p1_idx >= len(cells) or p2_idx >= len(cells): continue
                c1 = cells[p1_idx]
                c2 = cells[p2_idx]
                s1 = c1.get("state", 0)
                s2 = c2.get("state", 0)
                if s1 != s2 and s1 > 0 and s2 > 0:
                    painter.setPen(QPen(QColor(self.factions_data.get(p1_idx, "#ec4899")), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                    v1 = vor_mesh.vertices[v_indices[0]]
                    v2 = vor_mesh.vertices[v_indices[1]]
                    painter.drawLine(QPointF(float(v1[0]), float(v1[1])), QPointF(float(v2[0]), float(v2[1])))

        # Grid / Delaunay Edges (now toggled independently if needed, leaving as dashed for generic cell visualization)
        # painter.setPen(QPen(QColor("#04D361"), 1, Qt.PenStyle.DashLine))
        # painter.setBrush(Qt.BrushStyle.NoBrush)
        # for point_pair in vor_mesh.ridge_points:
        #     p1 = vor_mesh.points[point_pair[0]]
        #     p2 = vor_mesh.points[point_pair[1]]
        #     painter.drawLine(QPointF(float(p1[0]), float(p1[1])), QPointF(float(p2[0]), float(p2[1])))
            
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

        # Emblems (Shields on Capitals)
        if self.visibility_map.get("Emblems", True):
            for st in self.parent.map_engine.states:
                cap_cell_idx = st.get("capital_cell", 0)
                if cap_cell_idx > 0 and cap_cell_idx < len(cells):
                    cap_cell = cells[cap_cell_idx]
                    painter.save()
                    painter.translate(cap_cell["x"], cap_cell["y"] - 15)
                    path = QPainterPath()
                    path.moveTo(-8, -10)
                    path.lineTo(8, -10)
                    path.lineTo(8, 0)
                    path.quadTo(0, 15, 0, 15)
                    path.quadTo(-8, 0, -8, 0)
                    path.closeSubpath()
                    color = QColor(st.get("color", "#ff0000"))
                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(QColor("#000000"), 1))
                    painter.drawPath(path)
                    painter.restore()

        # Relief Icons (Mountains, Forests)
        if self.visibility_map.get("Relief Icons", True):
            for cell in cells:
                h = cell.get("h", 20)
                biome = cell.get("biome", "")
                if h >= 70:
                    # Mountain Icon
                    painter.save()
                    painter.translate(cell["x"], cell["y"])
                    painter.setBrush(QBrush(QColor("#64748b"))) # Slate
                    painter.setPen(QPen(QColor("#0f172a"), 1))
                    path = QPainterPath()
                    path.moveTo(0, -10)
                    path.lineTo(8, 5)
                    path.lineTo(-8, 5)
                    path.closeSubpath()
                    painter.drawPath(path)
                    # Snowcap
                    if h >= 85:
                        painter.setBrush(QBrush(QColor("#f8fafc")))
                        path2 = QPainterPath()
                        path2.moveTo(0, -10)
                        path2.lineTo(4, -2)
                        path2.lineTo(0, 0)
                        path2.lineTo(-4, -2)
                        path2.closeSubpath()
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.drawPath(path2)
                    painter.restore()
                elif "Forest" in biome or "Taiga" in biome:
                    # Tree Icon
                    painter.save()
                    painter.translate(cell["x"], cell["y"])
                    painter.setBrush(QBrush(QColor("#15803d")))
                    painter.setPen(QPen(QColor("#064e3b"), 1))
                    painter.drawEllipse(QRectF(-4, -6, 8, 8))
                    painter.setPen(QPen(QColor("#451a03"), 2))
                    painter.drawLine(QPointF(0, 2), QPointF(0, 6))
                    painter.restore()

        # Markers (Custom Points of Interest)
        if self.visibility_map.get("Markers", True):
            for marker in self.parent.map_engine.markers if hasattr(self.parent.map_engine, "markers") else []:
                cell = cells[marker["cell_idx"]]
                painter.save()
                painter.translate(cell["x"], cell["y"])
                painter.setBrush(QBrush(QColor("#ef4444")))
                painter.setPen(QPen(QColor("#7f1d1d"), 1))
                path = QPainterPath()
                path.moveTo(0, 0)
                path.quadTo(5, -5, 5, -10)
                path.arcTo(QRectF(-5, -15, 10, 10), 0, 180)
                path.quadTo(-5, -5, 0, 0)
                painter.drawPath(path)
                painter.setBrush(QBrush(QColor("#ffffff")))
                painter.drawEllipse(QRectF(-2, -12, 4, 4))
                painter.restore()

        painter.restore() # Reset pan/zoom transform before drawing UI overlays

        # UI Presentation Overlays
        width = self.width()
        height = self.height()

        if self.visibility_map.get("Grid", True):
            painter.setPen(QPen(QColor(255, 255, 255, 40), 1, Qt.PenStyle.SolidLine))
            grid_size = 100
            for x in range(0, width, grid_size):
                painter.drawLine(x, 0, x, height)
            for y in range(0, height, grid_size):
                painter.drawLine(0, y, width, y)

        if self.visibility_map.get("Coordinates", True):
            painter.setPen(QPen(QColor(255, 255, 255, 150)))
            painter.setFont(QFont("Consolas", 9))
            grid_size = 100
            for x in range(0, width, grid_size):
                lon = -180 + (x / width) * 360
                painter.drawText(x + 5, 15, f"{abs(int(lon))}°{'E' if lon >= 0 else 'W'}")
            for y in range(0, height, grid_size):
                lat = 90 - (y / height) * 180
                painter.drawText(5, y - 5, f"{abs(int(lat))}°{'N' if lat >= 0 else 'S'}")

        if self.visibility_map.get("Compass", True):
            painter.save()
            painter.translate(width - 60, 60)
            painter.setPen(Qt.PenStyle.NoPen)
            
            # Compass Rose
            for angle in [0, 90, 180, 270]:
                painter.rotate(angle)
                path_light = QPainterPath()
                path_light.moveTo(0, -35)
                path_light.lineTo(8, 0)
                path_light.lineTo(0, 0)
                path_light.closeSubpath()
                painter.setBrush(QBrush(QColor("#e2e8f0")))
                painter.drawPath(path_light)
                
                path_dark = QPainterPath()
                path_dark.moveTo(0, -35)
                path_dark.lineTo(-8, 0)
                path_dark.lineTo(0, 0)
                path_dark.closeSubpath()
                painter.setBrush(QBrush(QColor("#64748b")))
                painter.drawPath(path_dark)
                
            painter.setPen(QPen(QColor("#ffffff")))
            painter.setFont(QFont("Times New Roman", 12, QFont.Weight.Bold))
            painter.drawText(-6, -40, "N")
            painter.restore()

        if self.visibility_map.get("Scale Bar", True):
            painter.save()
            painter.translate(width - 250, height - 40)
            painter.setPen(QPen(QColor("#ffffff"), 1))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(0, -5, "0")
            painter.drawText(180, -5, "1000 mi")
            
            for i in range(4):
                painter.setBrush(QBrush(QColor("#ffffff") if i % 2 == 0 else QColor("#000000")))
                painter.drawRect(i * 50, 0, 50, 8)
                
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(0, 0, 200, 8)
            painter.restore()

        if self.visibility_map.get("Vignette", True):
            from PyQt6.QtGui import QRadialGradient
            gradient = QRadialGradient(width / 2, height / 2, max(width, height) / 1.5)
            gradient.setColorAt(0, QColor(0, 0, 0, 0))
            gradient.setColorAt(0.7, QColor(0, 0, 0, 80))
            gradient.setColorAt(1, QColor(0, 0, 0, 200))
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(0, 0, width, height)
