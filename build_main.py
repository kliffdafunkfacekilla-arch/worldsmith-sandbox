import os
import re

file_path = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\main.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the SQLite connections safely
def replace_conn(m):
    indent = m.group(1)
    db = m.group(2)
    return f'{indent}conn = sqlite3.connect({db}, timeout=15.0)\n{indent}conn.execute("PRAGMA journal_mode=WAL;")'

content = re.sub(r'^(\s*)conn\s*=\s*sqlite3\.connect\((.*?)\)', replace_conn, content, flags=re.MULTILINE)

# 2. Unified CSS Tokens
content = content.replace('background-color: #1a1a24', 'background-color: #0c0c10')

# 3. InteractiveLordsmithMapCanvas Caching & Double Buffering
class_start = content.find('class InteractiveLordsmithMapCanvas(QWidget):')
class_end = content.find('class AzgaarFactionSubsystemWidget(QWidget):')

new_canvas_class = '''class InteractiveLordsmithMapCanvas(QWidget):
    cell_hovered = pyqtSignal(int, int, str, str)
    cell_clicked = pyqtSignal(int)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setMinimumSize(800, 800)
        self.setMouseTracking(True)
        self.active_layer = "States"
        self.hovered_cell_idx = -1
        self._bg_cache = None
        self._cell_rects = {}

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._cache_cell_geometry()
        self._bg_cache = None

    def _cache_cell_geometry(self):
        engine = self.main_window.map_engine
        if not getattr(engine, 'cells', None): return
        
        scale_x = self.width() / 1000.0
        scale_y = self.height() / 1000.0
        self._cell_rects = {}
        
        for cell in engine.cells:
            cid = cell.get("i", 0)
            cx = int(cell.get("centroid_x", 0) * scale_x)
            cy = int(cell.get("centroid_y", 0) * scale_y)
            self._cell_rects[cid] = (cx, cy, cell)

    def draw_static_background(self):
        from PyQt6.QtCore import QRect
        from PyQt6.QtGui import QPainter, QPixmap, QColor, QBrush, QPen
        
        self._bg_cache = QPixmap(self.size())
        self._bg_cache.fill(QColor("#09090d"))
        
        painter = QPainter(self._bg_cache)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        engine = self.main_window.map_engine
        if not getattr(engine, 'cells', None):
            painter.setPen(QColor("#a0a0c0"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "WORLD NOT SYNTHESIZED YET\\nIngest notes and resolve AI reconciliation questions.")
            painter.end()
            return

        if not hasattr(self, 'tileset_img'):
            self.tileset_img = QPixmap(os.path.join(self.main_window.project_dir, 'assets', 'biome_tiles.jpg'))
            
            def get_rect(c, r):
                return QRect(c * 170 + 25, r * 204 + 10, 120, 120)

            self.biome_tiles = {
                "Tropical Rainforest": get_rect(0, 0), "Tropical Forest": get_rect(0, 0),
                "Temperate Forest": get_rect(1, 0), "Taiga": get_rect(2, 0),
                "Tundra": get_rect(3, 0), "Ice Cap / Glacier": get_rect(3, 0),
                "Savanna": get_rect(4, 0), "Shrubland / Chaparral": get_rect(4, 0),
                "Steppe / Grassland": get_rect(5, 0), "Arid Desert": get_rect(0, 1),
                "Cold Desert": get_rect(0, 1), "Alpine / Mountain": get_rect(2, 1),
                "Sunlit Coral Reef": get_rect(0, 2), "Sandy Lagoon & Seagrass Bed": get_rect(4, 2),
                "Benthopelagic Silt Plains": get_rect(2, 2), "Abyssal Barren Desert": get_rect(2, 2),
                "Abyssal Cryo-Brine Pool": get_rect(3, 2), "Oceanic Pelagic Barrens": get_rect(0, 3),
                "Deep Glass Sponge Reef": get_rect(4, 3), "Chemosynthetic Thermal Oasis": get_rect(4, 3),
                "Hydrothermal Chemotrophic Forest": get_rect(5, 3)
            }

        for cid, (cx, cy, cell) in self._cell_rects.items():
            h = cell.get("h", 20)

            if self.active_layer == "Biomes" and not self.tileset_img.isNull():
                biome = cell.get("biome", "")
                default_rect = get_rect(5, 0) if h >= 20 else get_rect(0, 3)
                src_rect = self.biome_tiles.get(biome, default_rect)
                painter.drawPixmap(QRect(cx - 16, cy - 16, 32, 32), self.tileset_img, src_rect)
            else:
                cell_brush = QBrush(QColor("#181825"))
                if self.active_layer == "States":
                    state_id = cell.get("state", 0)
                    color_hex = "#181825"
                    if state_id > 0 and hasattr(engine, 'states'):
                        color_hex = next((s["color"] for s in engine.states if s["id"] == state_id), "#181825")
                    cell_brush = QBrush(QColor(color_hex))
                elif self.active_layer == "Provinces":
                    prov_id = cell.get("province", 0)
                    prov_color = self.main_window.resolve_province_color_from_cache(prov_id)
                    cell_brush = QBrush(QColor(prov_color if prov_color else "#181825"))
                elif self.active_layer == "Biomes":
                    biome_colors = {
                        "Rainforest": "#106e2e", "Taiga": "#15803d", "Desert": "#ca8a04", 
                        "Marine": "#0c4a6e", "Deep Sea": "#082f49", "Tundra": "#38bdf8", "Ice": "#e0f2fe"
                    }
                    cell_brush = QBrush(QColor(biome_colors.get(cell.get("biome", ""), "#1e293b")))
                else:
                    val = int((h / 100.0) * 180) + 70
                    cell_brush = QBrush(QColor(0, val, val // 2) if h >= 20 else QColor(0, val // 4, val))
    
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(cell_brush)
                if self.active_layer != "Biomes":
                    painter.drawEllipse(cx - 10, cy - 10, 20, 20)

        painter.end()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor, QPen
        
        if self._bg_cache is None:
            self.draw_static_background()
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self._bg_cache:
            painter.drawPixmap(0, 0, self._bg_cache)

        if self.hovered_cell_idx != -1 and self.hovered_cell_idx in self._cell_rects:
            cx, cy, _ = self._cell_rects[self.hovered_cell_idx]
            painter.setPen(QPen(QColor("#04D361"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(cx - 12, cy - 12, 24, 24)

    def mouseMoveEvent(self, event):
        pos = event.position()
        if not self._cell_rects:
            return

        closest_cid = -1
        min_dist = float("inf")
        
        for cid, (cx, cy, cell) in self._cell_rects.items():
            dist = (pos.x() - cx)**2 + (pos.y() - cy)**2
            if dist < min_dist:
                min_dist = dist
                closest_cid = cid

        if min_dist < 900: # 30^2
            if closest_cid != self.hovered_cell_idx:
                self.hovered_cell_idx = closest_cid
                _, _, closest_cell = self._cell_rects[closest_cid]
                
                engine = self.main_window.map_engine
                faction_name = "Neutral Territory"
                if closest_cell.get("state", 0) > 0 and hasattr(engine, 'states'):
                    faction_name = next((s["name"] for s in engine.states if s["id"] == closest_cell["state"]), "Neutral Territory")
                
                self.cell_hovered.emit(closest_cid, closest_cell.get("h", 0), closest_cell.get("biome", ""), faction_name)
                self.update()
        else:
            self.hovered_cell_idx = -1
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.hovered_cell_idx != -1:
            self.cell_clicked.emit(self.hovered_cell_idx)

# =============================================================================
# WORKSPACE WIDGETS FOR ALL LORDSMITH SECTIONS
'''

content = content[:class_start] + new_canvas_class + content[class_end:]

with open('main_new.py', 'w', encoding='utf-8') as f:
    f.write(content)
