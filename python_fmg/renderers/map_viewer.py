import sys
import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPolygonF
from PyQt6.QtCore import QPointF

class MapViewerWidget(QWidget):
    cell_hovered = pyqtSignal(int, float, str, str)
    cell_clicked = pyqtSignal(int)  # Emit cell index on click for painting

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        
        self.elevation_data = {}  
        self.biomes_data = {}     
        self.factions_data = {}   
        self.magic_data = {}       # (q, r): magic type string
        self.layer_mode = "Elevation"  # "Elevation", "Biomes", "Political States", "Magic Layer"
        self.active_paint_magic = "Wild Magic"  # Currently selected magic brush

        self.grid_cells = []
        self.generate_d20_grid()

    def generate_d20_grid(self):
        self.grid_cells = []
        import math
        for face_idx in range(20):
            bx = 100 + (face_idx % 5) * 120 + (60 if (face_idx // 5) % 2 else 0)
            by = 80 + (face_idx // 5) * 110
            
            p1 = QPointF(bx, by)
            p2 = QPointF(bx + 100, by)
            p3 = QPointF(bx + 50, by + 90)
            
            for i in range(12):
                w1 = (i % 3 + 1) / 5.0
                w2 = ((i // 3) % 4 + 1) / 6.0
                w3 = 1.0 - w1 - w2
                
                cx = w1 * p1.x() + w2 * p2.x() + w3 * p3.x()
                cy = w1 * p1.y() + w2 * p2.y() + w3 * p3.y()
                
                q = face_idx * 100 + i
                r = face_idx * 50 - i
                
                self.grid_cells.append({
                    "idx": face_idx * 12 + i,
                    "q": q, "r": r,
                    "x": cx, "y": cy,
                    "face": face_idx
                })
                # Default magic data
                self.magic_data[(q, r)] = "None"

    def mouseMoveEvent(self, event):
        pos = event.position()
        import math
        closest_cell = None
        min_dist = 99999.0
        for cell in self.grid_cells:
            dist = math.sqrt((cell["x"] - pos.x())**2 + (cell["y"] - pos.y())**2)
            if dist < min_dist and dist < 20:
                min_dist = dist
                closest_cell = cell

        if closest_cell:
            q, r = closest_cell["q"], closest_cell["r"]
            elev = self.elevation_data.get((q, r), 0.0)
            biome = self.biomes_data.get((q, r), "Marine")
            state = self.factions_data.get((q, r), "Neutral")
            
            # Append active magic to status bar if hovering on Magic Layer
            if self.layer_mode == "Magic Layer":
                mag = self.magic_data.get((q, r), "None")
                biome = f"{biome} (Magic: {mag})"
                
            self.cell_hovered.emit(closest_cell["idx"], elev, biome, state)

    def mousePressEvent(self, event):
        # Support map painting on click
        pos = event.position()
        import math
        closest_cell = None
        min_dist = 99999.0
        for cell in self.grid_cells:
            dist = math.sqrt((cell["x"] - pos.x())**2 + (cell["y"] - pos.y())**2)
            if dist < min_dist and dist < 20:
                min_dist = dist
                closest_cell = cell

        if closest_cell and self.layer_mode == "Magic Layer":
            q, r = closest_cell["q"], closest_cell["r"]
            self.magic_data[(q, r)] = self.active_paint_magic
            self.update()
            self.cell_clicked.emit(closest_cell["idx"])

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        import math
        
        painter.fillRect(self.rect(), QBrush(QColor("#0d0d10")))
        
        for cell in self.grid_cells:
            q, r = cell["q"], cell["r"]
            cx, cy = cell["x"], cell["y"]
            
            if self.layer_mode == "Elevation":
                elev = self.elevation_data.get((q, r), 0)
                if elev < 20:
                    color = QColor(int((20 - elev) * 12), 30, int(80 + elev * 6))
                else:
                    color = QColor(int(20 + elev * 1.5), int(100 + elev), 20)
            elif self.layer_mode == "Biomes":
                biome = self.biomes_data.get((q, r), "Marine")
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
                color_hex = self.factions_data.get((q, r), "#18181b")
                color = QColor(color_hex)
            elif self.layer_mode == "Magic Layer":
                # Magic color palettes
                mag = self.magic_data.get((q, r), "None")
                if mag == "Wild Magic":
                    color = QColor("#a855f7") # Purple
                elif mag == "Abyssal Corruption":
                    color = QColor("#b91c1c") # Dark Red
                elif mag == "Ley Line Node":
                    color = QColor("#06b6d4") # Cyan
                elif mag == "Aether Storm":
                    color = QColor("#eab308") # Yellow
                else:
                    color = QColor("#27272a") # Dark gray
            else:
                color = QColor("#27272a")

            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor("#1e293b"), 1))
            
            radius = 12
            poly = QPolygonF()
            for angle in range(0, 360, 60):
                rad = math.radians(angle)
                poly.append(QPointF(cx + radius * math.cos(rad), cy + radius * math.sin(rad)))
            painter.drawPolygon(poly)

        # Draw boundaries
        painter.setPen(QPen(QColor("#04D361"), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for face_idx in range(20):
            bx = 100 + (face_idx % 5) * 120 + (60 if (face_idx // 5) % 2 else 0)
            by = 80 + (face_idx // 5) * 110
            p1 = QPointF(bx, by)
            p2 = QPointF(bx + 100, by)
            p3 = QPointF(bx + 50, by + 90)
            poly = QPolygonF([p1, p2, p3, p1])
            painter.drawPolygon(poly)
            
            painter.setPen(QColor("#4b5563"))
            painter.drawText(int(bx + 40), int(by + 40), str(face_idx))
            painter.setPen(QPen(QColor("#04D361"), 1, Qt.PenStyle.DashLine))
