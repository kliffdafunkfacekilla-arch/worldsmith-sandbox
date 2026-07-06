import sys
import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPolygonF, QPainterPath

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
        self.layer_mode = "Elevation"  
        self.active_paint_magic = "Wild Magic"  

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

        if closest_cell_idx is not None and self.layer_mode == "Magic Layer":
            self.magic_data[closest_cell_idx] = self.active_paint_magic
            self.update()
            self.cell_clicked.emit(closest_cell_idx)

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
            
            if self.layer_mode == "Elevation":
                elev = self.elevation_data.get(cell_id, 0)
                if elev < 20:
                    color = QColor(int((20 - elev) * 12), 30, int(80 + elev * 6))
                else:
                    color = QColor(int(20 + elev * 1.5), int(100 + elev), 20)
            elif self.layer_mode == "Biomes":
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
            elif self.layer_mode == "Political States":
                color_hex = self.factions_data.get(cell_id, "#18181b")
                color = QColor(color_hex)
            elif self.layer_mode == "Provinces":
                pid = cell.get("province", 0)
                if pid > 0 and pid in provinces_pool:
                    color_hex = provinces_pool[pid]["color"]
                else:
                    color_hex = "#27272a"
                color = QColor(color_hex)
            elif self.layer_mode == "Cultures":
                cid = cell.get("culture", 0)
                colors = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#6366f1", "#ec4899", "#8b5cf6"]
                color_hex = colors[cid % len(colors)] if cid > 0 else "#27272a"
                color = QColor(color_hex)
            elif self.layer_mode == "Magic Layer":
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
            elif self.layer_mode == "Production Goods":
                good = cell.get("good", "None")
                good_colors = {
                    "Grain": "#f59e0b", "Timber": "#15803d", "Spices": "#ec4899",
                    "Iron Ore": "#4b5563", "Bioluminescent Kelp": "#0d9488",
                    "Precious Metals": "#eab308", "Abyssal Pearls": "#8b5cf6", "Salt": "#f1f5f9"
                }
                color = QColor(good_colors.get(good, "#27272a"))
            else:
                color = QColor("#27272a")

            painter.fillPath(path, QBrush(color))
            painter.strokePath(path, QPen(QColor("#1e293b"), 0.5))

        # Render Flow Rivers overlay layer
        for cell in cells:
            if cell["r"] > 0:
                painter.setPen(QPen(QColor("#3b82f6"), max(1, int(cell["fl"] / 80)), Qt.PenStyle.SolidLine))
                for n in self.parent.map_engine.get_neighbors(cell["i"]):
                    nc = cells[n]
                    if nc["r"] == cell["r"] and nc["h"] < cell["h"]:
                        painter.drawLine(QPointF(cell["x"], cell["y"]), QPointF(nc["x"], nc["y"]))

        # Render Roads & Conduits trade route overlay lines
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
            
        # Draw military regiments overlay highlights
        for reg in self.parent.map_engine.military_regiments:
            cell_idx = reg["cell_idx"]
            for cell in cells:
                if cell["i"] == cell_idx:
                    painter.setBrush(QBrush(QColor("#ef4444") if "Guard" in reg["name"] else QColor("#eab308")))
                    painter.setPen(QPen(QColor("#ffffff"), 1))
                    painter.drawEllipse(QPointF(cell["x"], cell["y"]), 6, 6)
