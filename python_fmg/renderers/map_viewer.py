import sys
import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPolygonF
from PyQt6.QtCore import QPointF

class MapViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setMinimumSize(400, 400)
        self.elevation_data = {}  # (q, r): elevation
        self.biomes_data = {}     # (q, r): biome name
        self.factions_data = {}   # (q, r): faction color hex
        self.layer_mode = "Elevation"  # "Elevation", "Biomes", "Political States"

        self.grid_cells = []
        self.generate_d20_grid()

    def generate_d20_grid(self):
        self.grid_cells = []
        import math
        
        # Center triangle points on the screen coordinates
        for face_idx in range(20):
            # Calculate coordinates for 3 corners of the face triangle
            bx = 100 + (face_idx % 5) * 120 + (60 if (face_idx // 5) % 2 else 0)
            by = 80 + (face_idx // 5) * 110
            
            p1 = QPointF(bx, by)
            p2 = QPointF(bx + 100, by)
            p3 = QPointF(bx + 50, by + 90)
            
            # Subdivide face to create minor hexagonal cells inside each face
            for i in range(12):
                w1 = (i % 3 + 1) / 5.0
                w2 = ((i // 3) % 4 + 1) / 6.0
                w3 = 1.0 - w1 - w2
                
                cx = w1 * p1.x() + w2 * p2.x() + w3 * p3.x()
                cy = w1 * p1.y() + w2 * p2.y() + w3 * p3.y()
                
                q = face_idx * 100 + i
                r = face_idx * 50 - i
                
                self.grid_cells.append({
                    "q": q, "r": r,
                    "x": cx, "y": cy,
                    "face": face_idx
                })

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        import math
        
        # Draw background
        painter.fillRect(self.rect(), QBrush(QColor("#0d0d10")))
        
        # Render cells
        for cell in self.grid_cells:
            q, r = cell["q"], cell["r"]
            cx, cy = cell["x"], cell["y"]
            
            # Determine color based on active layer
            if self.layer_mode == "Elevation":
                elev = self.elevation_data.get((q, r), 0)
                if elev < 20:
                    color = QColor(10, 30, int(80 + elev * 2))  # Ocean
                else:
                    color = QColor(int(20 + elev * 1.5), int(100 + elev), 20)  # Land
            elif self.layer_mode == "Biomes":
                biome = self.biomes_data.get((q, r), "Marine")
                if biome == "Marine":
                    color = QColor("#1e293b")
                elif biome == "Hot Desert":
                    color = QColor("#eab308")
                elif biome == "Montane / Glacier":
                    color = QColor("#f1f5f9")
                elif biome == "Tropical Rainforest":
                    color = QColor("#065f46")
                elif biome == "Tundra":
                    color = QColor("#cbd5e1")
                else:
                    color = QColor("#15803d") # Grassland
            elif self.layer_mode == "Political States":
                color_hex = self.factions_data.get((q, r), "#18181b")
                color = QColor(color_hex)
            else:
                color = QColor("#27272a")

            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor("#1e293b"), 1))
            
            # Draw hexagon cell
            radius = 12
            poly = QPolygonF()
            for angle in range(0, 360, 60):
                rad = math.radians(angle)
                poly.append(QPointF(cx + radius * math.cos(rad), cy + radius * math.sin(rad)))
            painter.drawPolygon(poly)

        # Draw Icosahedral Projection Grid boundaries overlay
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
            
            # Draw face label index
            painter.setPen(QColor("#4b5563"))
            painter.drawText(int(bx + 40), int(by + 40), str(face_idx))
            painter.setPen(QPen(QColor("#04D361"), 1, Qt.PenStyle.DashLine))
