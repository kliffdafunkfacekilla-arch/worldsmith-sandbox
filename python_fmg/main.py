import os
import sys
import sqlite3
import json
import random
import math

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QLineEdit, QPushButton, QStatusBar, QMessageBox, QComboBox,
    QSlider, QFileDialog, QDialog, QListWidget, QInputDialog, QCheckBox,
    QFrame, QToolButton, QScrollArea, QMenu, QTableWidget, QTableWidgetItem, 
    QTreeView, QFormLayout, QDoubleSpinBox, QHeaderView, QColorDialog, QTabWidget,
    QProgressBar, QStackedWidget
)
from PyQt6.QtCore import Qt, QPointF, QPoint, pyqtSignal, QTimer, QDir, QThread, QObject
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPixmap, QImage,
    QTextCursor, QTextCharFormat, QFileSystemModel
)

# Add project root directory to path for nested imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from python_fmg.core.ai_worker import OllamaPromptWorker, LoreAuditWorker, AILoreIngestor, AILoreDriverWorker
from python_fmg.renderers.notebook_editor import MarkdownNotebookEditor
from python_fmg.core.azgaar_engine import AzgaarEngine, CosmosEngine

# =============================================================================
# COHESIVE RELATIONAL DATABASE INITIALIZATION WITH TEMPORAL MODULES
# =============================================================================
def setup_master_knowledge_db(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        cursor.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT UNIQUE NOT NULL, content TEXT NOT NULL, category TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cursor.execute("CREATE TABLE IF NOT EXISTS factions (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, color TEXT NOT NULL, gov_type TEXT DEFAULT 'Feudal Monarchy', dominant_cultures TEXT, dominant_religions TEXT, leaders TEXT, imports TEXT, exports TEXT, aggression_scale INTEGER DEFAULT 5, trade_scale INTEGER DEFAULT 5, explore_scale INTEGER DEFAULT 5, espionage_scale INTEGER DEFAULT 5, morale INTEGER DEFAULT 5, crime INTEGER DEFAULT 5, poverty INTEGER DEFAULT 5, freedom INTEGER DEFAULT 5, magic_stance TEXT DEFAULT 'Regulated', domain_type TEXT DEFAULT 'Both', treasury REAL DEFAULT 1000.0, capital_cell INTEGER, associated_note_id INTEGER, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS provinces (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, color TEXT NOT NULL, state_id INTEGER NOT NULL, governor_name TEXT, tax_rate REAL DEFAULT 10.0, local_morale INTEGER DEFAULT 5, local_crime INTEGER DEFAULT 5, local_poverty INTEGER DEFAULT 5, local_freedom INTEGER DEFAULT 5, local_magic_handling TEXT DEFAULT 'Lax Enforcement', associated_note_id INTEGER, FOREIGN KEY(state_id) REFERENCES factions(id) ON DELETE CASCADE, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS cultures (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, code TEXT NOT NULL, language_base TEXT DEFAULT 'Imperial', trait_type TEXT DEFAULT 'None', trait_modifier REAL DEFAULT 1.0, domain_type TEXT DEFAULT 'Both', associated_note_id INTEGER, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS cell_cultures_overlap (cell_id INTEGER NOT NULL, culture_id INTEGER NOT NULL, density REAL DEFAULT 1.0, PRIMARY KEY (cell_id, culture_id), FOREIGN KEY(culture_id) REFERENCES cultures(id) ON DELETE CASCADE)")
        cursor.execute("CREATE TABLE IF NOT EXISTS religions (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, color TEXT NOT NULL, religion_type TEXT DEFAULT 'Deity-Centric', is_official INTEGER DEFAULT 0, devotion INTEGER DEFAULT 5, recruit_rate INTEGER DEFAULT 5, rival_religion_ids TEXT, leaders TEXT, supreme_deity TEXT DEFAULT 'Solis', domain_type TEXT DEFAULT 'Both', holy_site_cell INTEGER, associated_note_id INTEGER, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS military (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, faction_id INTEGER, cell_idx INTEGER, troops_count INTEGER DEFAULT 1000, unit_type TEXT DEFAULT 'Infantry', tech_dependency_id INTEGER, associated_note_id INTEGER, FOREIGN KEY(faction_id) REFERENCES factions(id) ON DELETE SET NULL, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS defensive_structures (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, structure_type TEXT DEFAULT 'Watchtower', cell_idx INTEGER NOT NULL, defense_value INTEGER DEFAULT 5, garrison_capacity INTEGER DEFAULT 500, associated_note_id INTEGER, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS production_goods (cell_id INTEGER PRIMARY KEY, good TEXT NOT NULL, valuation REAL DEFAULT 1.0, is_finite INTEGER DEFAULT 0, max_capacity REAL DEFAULT 1000.0, current_capacity REAL DEFAULT 1000.0, is_market_center INTEGER DEFAULT 0, associated_note_id INTEGER, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS trade_routes (id INTEGER PRIMARY KEY AUTOINCREMENT, origin_cell INTEGER NOT NULL, destination_cell INTEGER NOT NULL, route_type TEXT DEFAULT 'Cobbled Road', safety_index REAL DEFAULT 1.0)")
        cursor.execute("CREATE TABLE IF NOT EXISTS cells (id INTEGER PRIMARY KEY, centroid_x REAL NOT NULL, centroid_y REAL NOT NULL, elevation INTEGER DEFAULT 20, moisture INTEGER DEFAULT 10, temperature INTEGER DEFAULT 15, biome TEXT DEFAULT 'Marine', plant_value INTEGER DEFAULT 5, prey_value INTEGER DEFAULT 5, predator_value INTEGER DEFAULT 5, state_id INTEGER, province_id INTEGER, culture_id INTEGER, religion_id INTEGER, FOREIGN KEY(state_id) REFERENCES factions(id) ON DELETE SET NULL, FOREIGN KEY(province_id) REFERENCES provinces(id) ON DELETE SET NULL, FOREIGN KEY(culture_id) REFERENCES cultures(id) ON DELETE SET NULL, FOREIGN KEY(religion_id) REFERENCES religions(id) ON DELETE SET NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS settlements (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, population REAL DEFAULT 10.0, cell_idx INTEGER, faction_id INTEGER, culture_id INTEGER, has_port INTEGER DEFAULT 0, has_university INTEGER DEFAULT 0, notable_locations TEXT, notable_persons_links TEXT, leaders_links TEXT, associated_note_id INTEGER, FOREIGN KEY(faction_id) REFERENCES factions(id) ON DELETE SET NULL, FOREIGN KEY(culture_id) REFERENCES cultures(id) ON DELETE SET NULL, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS geography_plates (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, movement_vector TEXT NOT NULL, volcanic_index REAL DEFAULT 1.0, associated_note_id INTEGER, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS magic_layers (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT NOT NULL, mode_type TEXT DEFAULT 'Point', origin_cell_idx INTEGER NOT NULL, termination_cell_idx INTEGER, radius_of_effect INTEGER DEFAULT 10, intensity REAL DEFAULT 1.0, effect_field_description TEXT, associated_note_id INTEGER, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS tech_eras (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, description TEXT, year_range TEXT NOT NULL, buff_type TEXT DEFAULT 'Extraction Speed', buff_modifier REAL DEFAULT 1.0, associated_note_id INTEGER, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS influence_factions (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, category TEXT DEFAULT 'Secret Society', leaders TEXT, headquarters_cell INTEGER, influence_effect_type TEXT DEFAULT 'Crime Catalyst', influence_intensity REAL DEFAULT 1.0, associated_note_id INTEGER, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS cell_shadow_influence (cell_id INTEGER NOT NULL, influence_faction_id INTEGER NOT NULL, grip_strength REAL DEFAULT 0.5, PRIMARY KEY (cell_id, influence_faction_id), FOREIGN KEY(influence_faction_id) REFERENCES influence_factions(id) ON DELETE CASCADE)")
        
        cursor.execute("CREATE TABLE IF NOT EXISTS calendar_config (id INTEGER PRIMARY KEY AUTOINCREMENT, year_length INTEGER DEFAULT 360, months_json TEXT, seasons_json TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS moons (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, period INTEGER DEFAULT 30, size_multiplier REAL DEFAULT 1.0, gravitational_tide_mod REAL DEFAULT 1.0, arcane_flux_modifier REAL DEFAULT 1.0)")
        cursor.execute("CREATE TABLE IF NOT EXISTS timeline_events (id INTEGER PRIMARY KEY AUTOINCREMENT, year INTEGER NOT NULL, day INTEGER DEFAULT 1, title TEXT NOT NULL, description TEXT, faction_id INTEGER, cell_idx INTEGER, associated_note_id INTEGER, FOREIGN KEY(faction_id) REFERENCES factions(id) ON DELETE SET NULL, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)")
        
        cursor.execute("CREATE TABLE IF NOT EXISTS note_map_bindings (note_id INTEGER, cell_idx INTEGER, PRIMARY KEY (note_id, cell_idx))")
        cursor.execute("CREATE TABLE IF NOT EXISTS markdown_map_bindings (title TEXT PRIMARY KEY, bind_type TEXT, bind_target TEXT, cell_idx INTEGER)")
        cursor.execute("CREATE TABLE IF NOT EXISTS inconsistencies (id INTEGER PRIMARY KEY AUTOINCREMENT, subject_type TEXT, subject_id INTEGER, description TEXT, status TEXT DEFAULT 'Active')")
        cursor.execute("CREATE TABLE IF NOT EXISTS map_snapshots (year INTEGER PRIMARY KEY, engine_state_json BLOB)")
        cursor.execute("CREATE TABLE IF NOT EXISTS markers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, type TEXT NOT NULL, cell_idx INTEGER NOT NULL, associated_note_id INTEGER, FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL)")

        cursor.execute("SELECT COUNT(*) FROM factions")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT OR IGNORE INTO factions (id, name, color, gov_type, aggression_scale, trade_scale, morale, magic_stance, domain_type, treasury) VALUES (1, 'Vulfurn Magocracy', '#ef4444', 'Magocracy', 8, 4, 7, 'Ruling Class', 'Both', 5000.0)")
            cursor.execute("INSERT OR IGNORE INTO factions (id, name, color, gov_type, aggression_scale, trade_scale, morale, magic_stance, domain_type, treasury) VALUES (2, 'Chipis Union', '#3b82f6', 'Merchant Oligarchy', 3, 9, 6, 'Repressed', 'Land', 8500.0)")
            cursor.execute("INSERT OR IGNORE INTO provinces (id, name, color, state_id, governor_name, local_morale, local_crime, local_magic_handling) VALUES (10, 'Shattered Marches', '#fca5a5', 1, 'Inquisitor Vael', 4, 8, 'Strict Inquisition')")
            cursor.execute("INSERT OR IGNORE INTO provinces (id, name, color, state_id, governor_name, local_morale, local_crime, local_magic_handling) VALUES (20, 'Ostraka Coastline', '#93c5fd', 2, 'Prefect Vance', 8, 2, 'Sanctuary')")
            cursor.execute("INSERT OR IGNORE INTO cultures (id, name, code, language_base, trait_type, trait_modifier) VALUES (50, 'Boreal Elves', 'BE', 'Elven', 'Arcane Catalyst', 1.25)")
            cursor.execute("INSERT OR IGNORE INTO cultures (id, name, code, language_base, trait_type, trait_modifier) VALUES (51, 'Abyssal Gill-kin', 'AG', 'DeepSpeech', 'Resource Drain', 0.85)")
            cursor.execute("INSERT OR IGNORE INTO religions (id, name, color, religion_type, devotion, recruit_rate, supreme_deity, domain_type) VALUES (201, 'Eternal Sun Creed', '#eab308', 'Deity-Centric', 9, 7, 'Solis the Unconquered', 'Both')")
            cursor.execute("INSERT OR IGNORE INTO influence_factions (id, name, category, leaders, influence_effect_type, influence_intensity) VALUES (301, 'The Obsidian Cartel', 'Criminal Cartel', 'Enzo the Silk Finger', 'Crime Catalyst', 1.50)")
            cursor.execute("INSERT OR IGNORE INTO calendar_config (id, year_length, months_json, seasons_json) VALUES (1, 420, '[]', '[]')")
            cursor.execute("INSERT OR IGNORE INTO moons (id, name, period, size_multiplier, gravitational_tide_mod, arcane_flux_modifier) VALUES (1, 'Vespera', 30, 1.2, 1.3, 1.5)")
            cursor.execute("INSERT OR IGNORE INTO moons (id, name, period, size_multiplier, gravitational_tide_mod, arcane_flux_modifier) VALUES (2, 'Aetheris', 45, 0.8, 0.7, 2.0)")
            cursor.execute("INSERT OR IGNORE INTO timeline_events (year, day, title, description, faction_id) VALUES (100, 50, 'The Foundation Stone', 'Sovereigns lay down the boundaries of the capitol.', 1)")
            cursor.execute("INSERT OR IGNORE INTO timeline_events (year, day, title, description, faction_id) VALUES (200, 150, 'The Sunder War', 'Border margins shatter during the iron ore skirmish.', 2)")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error establishing master knowledge database schema: {e}")


# =============================================================================
# HIGH-FIDELITY INTERACTIVE VECTOR MAP CANVAS (W/ DIRECT RE-ROUTING BINDS)
# =============================================================================
class InteractiveLordsmithMapCanvas(QWidget):
    cell_hovered = pyqtSignal(int, int, str, str) # id, h, biome, faction
    cell_clicked = pyqtSignal(int) # clicked cell index

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        self.active_layer = "States"
        self.hovered_cell_idx = -1



    def paintEvent(self, event):
        from PyQt6.QtCore import QRect
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#09090d"))

        engine = self.main_window.map_engine
        if not getattr(engine, 'cells', None):
            painter.setPen(QColor("#a0a0c0"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "WORLD NOT SYNTHESIZED YET\\nIngest notes and resolve AI reconciliation questions.")
            return

        scale_x = self.width() / 1000.0
        scale_y = self.height() / 1000.0

        if not hasattr(self, 'tileset_img'):
            self.tileset_img = QPixmap(os.path.join(self.main_window.project_dir, 'assets', 'biome_tiles.jpg'))
            
            def get_rect(c, r):
                # 1024x1024 divided by 6 cols, 5 rows = ~170x204 per cell
                # Crop 120x120 from top-center to avoid text labels
                return QRect(c * 170 + 25, r * 204 + 10, 120, 120)

            # Map the exact AzgaarEngine biomes to the provided image grid
            self.biome_tiles = {
                # Row 0
                "Tropical Rainforest": get_rect(0, 0),
                "Tropical Forest": get_rect(0, 0),
                "Temperate Forest": get_rect(1, 0),
                "Taiga": get_rect(2, 0),
                "Tundra": get_rect(3, 0),
                "Ice Cap / Glacier": get_rect(3, 0),
                "Savanna": get_rect(4, 0),
                "Shrubland / Chaparral": get_rect(4, 0),
                "Steppe / Grassland": get_rect(5, 0),
                
                # Row 1
                "Arid Desert": get_rect(0, 1),
                "Cold Desert": get_rect(0, 1),
                "Alpine / Mountain": get_rect(2, 1),
                
                # Row 2 (Coastal/Benthic)
                "Sunlit Coral Reef": get_rect(0, 2),
                "Sandy Lagoon & Seagrass Bed": get_rect(4, 2),
                "Benthopelagic Silt Plains": get_rect(2, 2),
                "Abyssal Barren Desert": get_rect(2, 2),
                "Abyssal Cryo-Brine Pool": get_rect(3, 2),
                
                # Row 3 (Open Ocean)
                "Oceanic Pelagic Barrens": get_rect(0, 3),
                "Deep Glass Sponge Reef": get_rect(4, 3),
                "Chemosynthetic Thermal Oasis": get_rect(4, 3),
                "Hydrothermal Chemotrophic Forest": get_rect(5, 3)
            }

        for cell in engine.cells:
            cid = cell.get("i", 0)
            cx, cy = int(cell.get("centroid_x", 0) * scale_x), int(cell.get("centroid_y", 0) * scale_y)
            h = cell.get("h", 20)

            # Draw Tile if Biomes layer and tileset is loaded
            if self.active_layer == "Biomes" and not self.tileset_img.isNull():
                biome = cell.get("biome", "")
                # Fallback to Pelagic Open Ocean (0,3) if ocean, or Grassland (5,0) if land
                default_rect = get_rect(5, 0) if h >= 20 else get_rect(0, 3)
                src_rect = self.biome_tiles.get(biome, default_rect)
                
                # Draw the hex tile centered on the point (scaled to 32x32 for map)
                painter.drawPixmap(QRect(cx - 16, cy - 16, 32, 32), self.tileset_img, src_rect)
            else:
                # Fallback to Solid Color Ellipse
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

            # Hover highlight
            if cid == self.hovered_cell_idx:
                painter.setPen(QPen(QColor("#04D361"), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(cx - 12, cy - 12, 24, 24)

    def mouseMoveEvent(self, event):
        pos = event.position()
        engine = self.main_window.map_engine
        if not getattr(engine, 'cells', None): return

        scale_x = self.width() / 1000.0
        scale_y = self.height() / 1000.0

        closest_cell = None
        min_dist = float("inf")
        for cell in engine.cells:
            cx, cy = cell.get("centroid_x",0) * scale_x, cell.get("centroid_y",0) * scale_y
            dist = math.sqrt((pos.x() - cx)**2 + (pos.y() - cy)**2)
            if dist < min_dist:
                min_dist = dist
                closest_cell = cell

        if closest_cell and min_dist < 30:
            cid = closest_cell.get("i", 0)
            if cid != self.hovered_cell_idx:
                self.hovered_cell_idx = cid
                faction_name = "Neutral Territory"
                if closest_cell.get("state", 0) > 0 and hasattr(engine, 'states'):
                    faction_name = next((s["name"] for s in engine.states if s["id"] == closest_cell["state"]), "Neutral Territory")
                self.cell_hovered.emit(cid, closest_cell.get("h", 0), closest_cell.get("biome", ""), faction_name)
                self.update()
        else:
            self.hovered_cell_idx = -1
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.hovered_cell_idx != -1:
            self.cell_clicked.emit(self.hovered_cell_idx)

# =============================================================================
# WORKSPACE WIDGETS FOR ALL LORDSMITH SECTIONS
# =============================================================================
class AzgaarFactionSubsystemWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db_path = main_window.db_path
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>🏳️ Sovereign States & Countries Ledger</b>"))
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Color", "Gov Type", "Aggress (1-10)", "Trade (1-10)", "Freedom (1-10)", "Magic Stance", "Domain"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("QTableWidget { background-color: #1a1a24; gridline-color: #29292E; }")
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        layout.addWidget(self.table)
        btn_add = QPushButton("➕ Add Sovereign State")
        btn_add.clicked.connect(self.add_state)
        layout.addWidget(btn_add)
        
    def refresh_grid(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, color, gov_type, aggression_scale, trade_scale, freedom, magic_stance, domain_type FROM factions")
            rows = cursor.fetchall()
            conn.close()
            self.table.setRowCount(len(rows))
            for r_idx, (fid, name, color, gov, agg, trd, free, magic, dom) in enumerate(rows):
                self.table.setItem(r_idx, 0, QTableWidgetItem(str(fid)))
                self.table.setItem(r_idx, 1, QTableWidgetItem(name))
                color_btn = QPushButton()
                color_btn.setFixedSize(24, 20)
                color_btn.setStyleSheet(f"background-color: {color}; border: 1px solid #fff;")
                color_btn.clicked.connect(lambda _, r=r_idx, s=fid: self.pick_color(r, s))
                self.table.setCellWidget(r_idx, 2, color_btn)
                self.table.setItem(r_idx, 3, QTableWidgetItem(str(gov)))
                self.table.setItem(r_idx, 4, QTableWidgetItem(str(agg)))
                self.table.setItem(r_idx, 5, QTableWidgetItem(str(trd)))
                self.table.setItem(r_idx, 6, QTableWidgetItem(str(free)))
                self.table.setItem(r_idx, 7, QTableWidgetItem(str(magic)))
                self.table.setItem(r_idx, 8, QTableWidgetItem(str(dom)))
            self.table.itemChanged.connect(self.handle_edited)
        except Exception as e:
            pass
        self.table.blockSignals(False)

    def handle_edited(self, item):
        row = item.row()
        fid = int(self.table.item(row, 0).text())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if item.column() == 1:
            cursor.execute("UPDATE factions SET name = ? WHERE id = ?", (item.text(), fid))
        elif item.column() == 3:
            cursor.execute("UPDATE factions SET gov_type = ? WHERE id = ?", (item.text(), fid))
        conn.commit()
        conn.close()
        self.main_window.run_local_lore_reconciliation()

    def pick_color(self, row, fid):
        color = QColorDialog.getColor()
        if color.isValid():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE factions SET color = ? WHERE id = ?", (color.name(), fid))
            conn.commit()
            conn.close()
            self.refresh_grid()
            self.main_window.map_viewer_canvas.update()

    def add_state(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        new_id = random.randint(100, 9999)
        hex_color = f"#{random.randint(0, 0xFFFFFF):06x}"
        cursor.execute("INSERT INTO factions (id, name, color, gov_type, aggression_scale, trade_scale, freedom, magic_stance, domain_type) VALUES (?, ?, ?, 'Feudal Kingdom', 5, 5, 5, 'Regulated', 'Both')", (new_id, f"State_{new_id}", hex_color))
        conn.commit()
        conn.close()
        self.refresh_grid()
        self.main_window.run_local_lore_reconciliation()

    def on_table_selection_changed(self):
        ranges = self.table.selectedRanges()
        if not ranges: return
        row = ranges[0].topRow()
        fid = int(self.table.item(row, 0).text())
        self.main_window.update_parameter_inspector("factions", fid)

class AzgaarProvinceSubsystemWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db_path = main_window.db_path
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>🛡️ Internal State Provinces</b>"))
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Province Name", "Color", "Governor", "Local Morale", "Magic Handling"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("QTableWidget { background-color: #1a1a24; }")
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        layout.addWidget(self.table)
        btn_add = QPushButton("➕ Add State Province")
        btn_add.clicked.connect(self.add_province)
        layout.addWidget(btn_add)
        
    def refresh_grid(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, color, governor_name, local_morale, local_magic_handling FROM provinces")
            rows = cursor.fetchall()
            conn.close()
            self.table.setRowCount(len(rows))
            for r_idx, (pid, name, color, gov, morale, magic) in enumerate(rows):
                self.table.setItem(r_idx, 0, QTableWidgetItem(str(pid)))
                self.table.setItem(r_idx, 1, QTableWidgetItem(name))
                color_btn = QPushButton()
                color_btn.setFixedSize(24, 20)
                color_btn.setStyleSheet(f"background-color: {color}; border: 1px solid #fff;")
                color_btn.clicked.connect(lambda _, r=r_idx, p=pid: self.pick_color(r, p))
                self.table.setCellWidget(r_idx, 2, color_btn)
                self.table.setItem(r_idx, 3, QTableWidgetItem(str(gov if gov else "Vacant")))
                self.table.setItem(r_idx, 4, QTableWidgetItem(str(morale)))
                self.table.setItem(r_idx, 5, QTableWidgetItem(str(magic)))
        except Exception as e:
            pass
        self.table.blockSignals(False)

    def pick_color(self, row, pid):
        color = QColorDialog.getColor()
        if color.isValid():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE provinces SET color = ? WHERE id = ?", (color.name(), pid))
            conn.commit()
            conn.close()
            self.refresh_grid()
            self.main_window.map_viewer_canvas.update()

    def add_province(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        new_id = random.randint(100, 9999)
        hex_color = f"#{random.randint(0, 0xFFFFFF):06x}"
        cursor.execute("INSERT INTO provinces (id, name, color, state_id, governor_name, local_morale, local_magic_handling) VALUES (?, ?, ?, 1, 'Noble Governor', 5, 'Lax Enforcement')", (new_id, f"Province_{new_id}", hex_color))
        conn.commit()
        conn.close()
        self.refresh_grid()
        self.main_window.run_local_lore_reconciliation()

    def on_table_selection_changed(self):
        ranges = self.table.selectedRanges()
        if not ranges: return
        row = ranges[0].topRow()
        pid = int(self.table.item(row, 0).text())
        self.main_window.update_parameter_inspector("provinces", pid)


class AzgaarReligionSubsystemWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db_path = main_window.db_path
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>✨ Religions Matrix</b>"))
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Type", "Official", "Devotion", "Recruit Rate", "Supreme Deity", "Domain"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("QTableWidget { background-color: #1a1a24; }")
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        layout.addWidget(self.table)
        btn_add = QPushButton("➕ Instate New Religion")
        btn_add.clicked.connect(self.add_religion)
        layout.addWidget(btn_add)

    def refresh_grid(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, religion_type, is_official, devotion, recruit_rate, supreme_deity, domain_type FROM religions")
            rows = cursor.fetchall()
            conn.close()
            self.table.setRowCount(len(rows))
            for r_idx, (rid, name, rel_type, official, devotion, recruit, deity, domain) in enumerate(rows):
                self.table.setItem(r_idx, 0, QTableWidgetItem(str(rid)))
                self.table.setItem(r_idx, 1, QTableWidgetItem(name))
                self.table.setItem(r_idx, 2, QTableWidgetItem(str(rel_type)))
                self.table.setItem(r_idx, 3, QTableWidgetItem("Yes" if official else "No"))
                self.table.setItem(r_idx, 4, QTableWidgetItem(str(devotion)))
                self.table.setItem(r_idx, 5, QTableWidgetItem(str(recruit)))
                self.table.setItem(r_idx, 6, QTableWidgetItem(str(deity)))
                self.table.setItem(r_idx, 7, QTableWidgetItem(str(domain)))
        except Exception as e: pass
        self.table.blockSignals(False)

    def add_religion(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        new_id = random.randint(100, 9999)
        cursor.execute("INSERT INTO religions (id, name, color, religion_type, devotion, recruit_rate, supreme_deity, domain_type) VALUES (?, ?, '#ffd700', 'Deity-Centric', 5, 5, 'Sun God', 'Both')", (new_id, f"Creed_{new_id}"))
        conn.commit()
        conn.close()
        self.refresh_grid()
        self.main_window.run_local_lore_reconciliation()

    def on_table_selection_changed(self):
        ranges = self.table.selectedRanges()
        if not ranges: return
        row = ranges[0].topRow()
        rid = int(self.table.item(row, 0).text())
        self.main_window.update_parameter_inspector("religions", rid)


class AzgaarCultureSubsystemWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db_path = main_window.db_path
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>🌐 Cultures & Species Registry</b>"))
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Lang Code", "Primary Syllables", "Trait", "Domain"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("QTableWidget { background-color: #1a1a24; }")
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        layout.addWidget(self.table)
        btn_add = QPushButton("➕ Seed New Culture")
        btn_add.clicked.connect(self.add_culture)
        layout.addWidget(btn_add)

    def refresh_grid(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, code, language_base, trait_type, domain_type FROM cultures")
            rows = cursor.fetchall()
            conn.close()
            self.table.setRowCount(len(rows))
            for r_idx, (cid, name, code, lang, trait, domain) in enumerate(rows):
                self.table.setItem(r_idx, 0, QTableWidgetItem(str(cid)))
                self.table.setItem(r_idx, 1, QTableWidgetItem(name))
                self.table.setItem(r_idx, 2, QTableWidgetItem(str(code)))
                self.table.setItem(r_idx, 3, QTableWidgetItem(str(lang)))
                self.table.setItem(r_idx, 4, QTableWidgetItem(str(trait)))
                self.table.setItem(r_idx, 5, QTableWidgetItem(str(domain)))
        except Exception as e: pass
        self.table.blockSignals(False)

    def add_culture(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        new_id = random.randint(100, 9999)
        cursor.execute("INSERT INTO cultures (id, name, code, language_base, trait_type, trait_modifier, domain_type) VALUES (?, ?, 'CUL', 'Common', 'Income Boost', 1.10, 'Both')", (new_id, f"Culture_{new_id}"))
        conn.commit()
        conn.close()
        self.refresh_grid()

    def on_table_selection_changed(self):
        ranges = self.table.selectedRanges()
        if not ranges: return
        row = ranges[0].topRow()
        cid = int(self.table.item(row, 0).text())
        self.main_window.update_parameter_inspector("cultures", cid)


class AzgaarGenericSubsystemWidget(QWidget):
    """Generic catch-all grid for the remaining tables to prevent boilerplate."""
    def __init__(self, main_window, table_name, title, columns):
        super().__init__()
        self.main_window = main_window
        self.db_path = main_window.db_path
        self.table_name = table_name
        self.columns = columns
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>{title}</b>"))
        self.table = QTableWidget()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels([c.upper() for c in columns])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("QTableWidget { background-color: #1a1a24; }")
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        layout.addWidget(self.table)
        
    def refresh_grid(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(f"SELECT {','.join(self.columns)} FROM {self.table_name}")
            rows = cursor.fetchall()
            conn.close()
            self.table.setRowCount(len(rows))
            for r_idx, row_data in enumerate(rows):
                for c_idx, val in enumerate(row_data):
                    self.table.setItem(r_idx, c_idx, QTableWidgetItem(str(val) if val is not None else ""))
        except Exception as e: pass
        self.table.blockSignals(False)

    def on_table_selection_changed(self):
        ranges = self.table.selectedRanges()
        if not ranges: return
        row = ranges[0].topRow()
        item_id = self.table.item(row, 0).text()
        self.main_window.update_parameter_inspector(self.table_name, item_id)


# =============================================================================
# PROJECT STARTUP WIZARD
# =============================================================================
class ProjectStartupWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_dir = None
        self.setWindowTitle("Lordsmith Studio Startup")
        self.resize(460, 240)
        self.setStyleSheet("background-color: #111116; color: #EEEEF8; font-family: Arial;")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>🌌 Welcome to Lordsmith Studio</h2>"))
        btn_new = QPushButton("🎲 Create Fresh Workspace")
        btn_new.clicked.connect(self.action_new_project)
        layout.addWidget(btn_new)

    def action_new_project(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Project Folder Directory")
        if dir_path:
            self.selected_dir = dir_path
            self.accept()

# =============================================================================
# MAIN WINDOW ARCHITECTURE
# =============================================================================
class LordsmithStudioMainWindow(QMainWindow):

    def __init__(self, project_dir):
        super().__init__()
        self.project_dir = os.path.abspath(project_dir)
        self.setWindowTitle("Lordsmith Studio Workspace")
        self.resize(1650, 950)
        self.setStyleSheet("background-color: #111116; color: #EEEEF8; QLineEdit, QTextEdit, QTableWidget { background-color: #1a1a24; border: 1px solid #333333; } QPushButton { background-color: #29293a; padding: 5px; }")
        
        self.db_path = os.path.join(self.project_dir, "lore_forge_world.db")
        # Ensure fresh run if schema gets borked during sandbox testing
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        setup_master_knowledge_db(self.db_path)

        self.map_engine = AzgaarEngine()

        # Build Export Menu
        file_menu = self.menuBar().addMenu("File")
        
        action_export_geojson = file_menu.addAction("Export GeoJSON Framework")
        action_export_geojson.triggered.connect(self.action_export_geojson)
        
        action_export_wiki = file_menu.addAction("Export Static HTML Wiki")
        action_export_wiki.triggered.connect(self.action_export_wiki)

        central_container = QWidget()

        self.setCentralWidget(central_container)
        main_h_layout = QHBoxLayout(central_container)

        self.panels_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_h_layout.addWidget(self.panels_splitter)

        # Left panel: Note editor
        self.panel_left = QWidget()
        pl_lay = QVBoxLayout(self.panel_left)
        pl_lay.addWidget(QLabel("<b>✍️ Narrative Lore Writer</b>"))
        self.note_writer = MarkdownNotebookEditor(self.panel_left)
        pl_lay.addWidget(self.note_writer, 1)
        self.note_writer.spatial_bind_clicked.connect(self.handle_spatial_bind_clicked)
        self.note_writer.wiki_link_clicked.connect(self.handle_wiki_link_clicked)
        self.panels_splitter.addWidget(self.panel_left)

        # Middle panel: Subsystem Registry Stack
        self.panel_middle = QWidget()
        pm_lay = QVBoxLayout(self.panel_middle)
        self.cb_subject_selector = QComboBox()
        pm_lay.addWidget(self.cb_subject_selector)
        self.subsystem_stack = QStackedWidget()
        pm_lay.addWidget(self.subsystem_stack, 1)
        self.panels_splitter.addWidget(self.panel_middle)

        # Initialize Subsystem Widgets
        self.w_factions = AzgaarFactionSubsystemWidget(self)
        self.w_provinces = AzgaarProvinceSubsystemWidget(self)
        self.w_religions = AzgaarReligionSubsystemWidget(self)
        self.w_cultures = AzgaarCultureSubsystemWidget(self)
        
        self.subsystems = [
            ("Sovereign States", self.w_factions),
            ("Provinces", self.w_provinces),
            ("Religions", self.w_religions),
            ("Cultures", self.w_cultures),
            ("Military Regiments", AzgaarGenericSubsystemWidget(self, "military", "⚔️ Regiments", ["id", "name", "faction_id", "troops_count", "unit_type"])),
            ("Defensive Structures", AzgaarGenericSubsystemWidget(self, "defensive_structures", "🏰 Defenses", ["id", "name", "structure_type", "defense_value"])),
            ("Economic Commodities", AzgaarGenericSubsystemWidget(self, "production_goods", "📦 Commodities", ["cell_id", "good", "valuation", "is_market_center"])),
            ("Trade Routes", AzgaarGenericSubsystemWidget(self, "trade_routes", "🛤️ Routes", ["id", "origin_cell", "destination_cell", "route_type"])),
            ("Burgs & Settlements", AzgaarGenericSubsystemWidget(self, "settlements", "🏘️ Burgs", ["id", "name", "population", "has_port"])),
            ("Geography Tectonics", AzgaarGenericSubsystemWidget(self, "geography_plates", "🌍 Plates", ["id", "name", "movement_vector"])),
            ("Magic Leylines", AzgaarGenericSubsystemWidget(self, "magic_layers", "✨ Magic", ["id", "label", "mode_type", "intensity"])),
            ("Tech Eras", AzgaarGenericSubsystemWidget(self, "tech_eras", "⚙️ Tech", ["id", "name", "year_range"])),
            ("Influence Factions", AzgaarGenericSubsystemWidget(self, "influence_factions", "🕸️ Shadow Network", ["id", "name", "category", "influence_intensity"])),
            ("Calendar Rules", AzgaarGenericSubsystemWidget(self, "calendar_config", "📅 Calendar", ["id", "year_length"])),
            ("Planetary Moons", AzgaarGenericSubsystemWidget(self, "moons", "🌘 Moons", ["id", "name", "period", "gravitational_tide_mod"])),
            ("Timeline Events", AzgaarGenericSubsystemWidget(self, "timeline_events", "📜 Historical Events", ["id", "year", "title", "faction_id"])),
            ("Markers", AzgaarGenericSubsystemWidget(self, "markers", "📍 Markers", ["id", "name", "type"]))
        ]
        
        for name, widget in self.subsystems:
            self.cb_subject_selector.addItem(name)
            self.subsystem_stack.addWidget(widget)
            
        self.cb_subject_selector.currentIndexChanged.connect(self.on_subject_changed)
        
        # Right Panel: Inspector and Interactive Canvas
        self.panel_right = QWidget()
        pr_lay = QVBoxLayout(self.panel_right)
        
        self.btn_toggle_map = QPushButton("👁️ Show Interactive Canvas")
        self.btn_toggle_map.setCheckable(True)
        self.btn_toggle_map.clicked.connect(self.toggle_map_view)
        pr_lay.addWidget(self.btn_toggle_map)
        
        self.btn_upload_heightmap = QPushButton("🗺️ Upload Custom Heightmap Image")
        self.btn_upload_heightmap.clicked.connect(self.action_upload_heightmap)
        pr_lay.addWidget(self.btn_upload_heightmap)
        
        self.right_stack = QStackedWidget()
        self.form_widget = QScrollArea()
        self.form_widget.setWidgetResizable(True)
        self.form_inner = QWidget()
        self.form_layout = QFormLayout(self.form_inner)
        self.form_widget.setWidget(self.form_inner)
        self.right_stack.addWidget(self.form_widget)
        
        self.map_viewer_canvas = InteractiveLordsmithMapCanvas(self)
        self.right_stack.addWidget(self.map_viewer_canvas)
        pr_lay.addWidget(self.right_stack, 1)
        
        self.panels_splitter.addWidget(self.panel_right)
        
        self.on_subject_changed(0)

    def on_subject_changed(self, index):
        self.subsystem_stack.setCurrentIndex(index)
        widget = self.subsystem_stack.widget(index)
        if hasattr(widget, 'refresh_grid'):
            widget.refresh_grid()

    def resolve_province_color_from_cache(self, prov_id):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT color FROM provinces WHERE id=?", (prov_id,))
            res = cursor.fetchone()
            conn.close()
            if res: return res[0]
        except: pass
        return None

    def run_local_lore_reconciliation(self):
        print("Reconciliation Triggered: Syncing AI knowledge vectors...")
        
    def update_parameter_inspector(self, table_name, item_id):
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item.widget(): item.widget().setParent(None)
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            cols = cursor.fetchall()
            pk_col = cols[0][1] if cols else "id"
            cursor.execute(f"SELECT * FROM {table_name} WHERE {pk_col}=?", (item_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row: return
            
            for col, val in zip(cols, row):
                col_name = col[1]
                t = QLineEdit(str(val) if val is not None else "")
                self.form_layout.addRow(f"{col_name}:", t)
                
            btn = QPushButton("Save Changes")
            self.form_layout.addRow(btn)
        except Exception as e:
            print(f"Inspector error: {e}")

    def toggle_map_view(self, checked):
        self.right_stack.setCurrentIndex(1 if checked else 0)

    def action_upload_heightmap(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Heightmap Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            try:
                # Seed Voronoi if empty
                if not getattr(self.map_engine, 'cells', None):
                    self.map_engine.generate_voronoi_mesh(1000)
                # Run the pipeline with the image
                self.map_engine.run_heightmap_pipeline(file_path)
                if hasattr(self.map_engine, 'run_biomes_climate'):
                    self.map_engine.run_biomes_climate()
                # Switch to map view
                self.btn_toggle_map.setChecked(True)
                self.toggle_map_view(True)
                self.map_viewer_canvas.update()
                QMessageBox.information(self, "Success", "Custom heightmap applied successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to apply heightmap: {e}")


    def action_export_geojson(self):
        from python_fmg.core.export_engine import WorldsmithExportEngine
        out_path, _ = QFileDialog.getSaveFileName(self, "Export GeoJSON", os.path.join(self.project_dir, "map.geojson"), "GeoJSON Files (*.geojson)")
        if out_path:
            try:
                exporter = WorldsmithExportEngine(self)
                exporter.compile_geojson_framework(out_path)
                QMessageBox.information(self, "Export Complete", f"GeoJSON exported to: {out_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export GeoJSON: {e}")

    def action_export_wiki(self):
        from python_fmg.core.wiki_compiler import WikiCompiler
        out_dir = QFileDialog.getExistingDirectory(self, "Select Wiki Export Directory", self.project_dir)
        if out_dir:
            try:
                compiler = WikiCompiler(db_path=self.db_path, output_dir=out_dir)
                success, msg = compiler.compile_wiki()
                if success:
                    QMessageBox.information(self, "Export Complete", msg)
                else:
                    QMessageBox.critical(self, "Export Error", f"Failed to compile Wiki: {msg}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Exception compiling Wiki: {e}")


    def handle_spatial_bind_clicked(self, cell_idx):
        if not self.btn_toggle_map.isChecked():
            self.btn_toggle_map.setChecked(True)
            self.toggle_map_view(True)
        # Emulate a hover/click on the cell
        self.map_viewer_canvas.hovered_cell_idx = cell_idx
        self.map_viewer_canvas.update()
        
    def handle_wiki_link_clicked(self, title):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM notes WHERE title = ?", (title,))
            res = cursor.fetchone()
            conn.close()
            if res:
                self.note_writer.setText(res[0])
            else:
                QMessageBox.information(self, "Note Not Found", f"No lore entry found for: {title}")
        except Exception as e:
            print(f"Error fetching note: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    wizard = ProjectStartupWizard()
    if wizard.exec() == QDialog.DialogCode.Accepted and wizard.selected_dir:
        window = LordsmithStudioMainWindow(wizard.selected_dir)
        window.show()
        sys.exit(app.exec())
