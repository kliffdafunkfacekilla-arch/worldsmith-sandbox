import os
import sys
import sqlite3
import json
import urllib.request
import random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QLineEdit, QPushButton, QStatusBar, QMessageBox, QComboBox,
    QSlider, QFileDialog, QDialog, QListWidget, QInputDialog, QCheckBox,
    QFrame, QToolButton, QScrollArea, QMenu, QTableWidget, QTableWidgetItem, 
    QTreeView, QFormLayout, QDoubleSpinBox, QHeaderView, QColorDialog,
    QTabWidget, QGroupBox
)
from PyQt6.QtCore import Qt, QPointF, QPoint, pyqtSignal, QTimer, QDir
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPixmap,
    QTextCursor, QTextCharFormat, QFileSystemModel
)

# Add project root directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from python_fmg.core.ai_worker import OllamaPromptWorker, LoreAuditWorker, AILoreIngestor, AILoreDriverWorker
from python_fmg.renderers.map_viewer import MapViewerWidget
from python_fmg.renderers.notebook_editor import MarkdownNotebookEditor
from python_fmg.core.azgaar_engine import AzgaarEngine, CosmosEngine
from python_fmg.core.wiki_compiler import WikiCompiler
from python_fmg.renderers.celestial_widget import CelestialPreviewWidget
from python_fmg.core.template_manager import TemplateManager
from python_fmg.ui.map_binding import MapBindingDialog
from python_fmg.core.emblem_generator import EmblemGenerator
from python_fmg.core.burg_generator import BurgGenerator

def compute_atmospheric_dimension_layer(altitude_km):
    """
    Applies the sequence formula to determine if a metric coordinate falls into 
    an active Sky Layer canvas or an invisible system buffer zone.
    Main Ground Map: 0km to 1km
    Sky Layer 1: 1km to 2km (Buffer skipped: 2km to 3km)
    Sky Layer 2: 3km to 4km
    """
    if altitude_km <= 1.0:
        return "surface", 0.0, 1.0
        
    layer_idx = int((altitude_km + 1) // 2)
    bottom_bound = (2 * layer_idx) - 1
    top_bound = 2 * layer_idx
    
    if bottom_bound <= altitude_km <= top_bound:
        return f"sky_{layer_idx}", float(bottom_bound), float(top_bound)
    else:
        return "system_buffer_zone", float(top_bound), float(top_bound + 1)


# =============================================================================
# DIALOG: Settlement Street Map Preview
# =============================================================================
class BurgMapDialog(QDialog):
    def __init__(self, burg, cell_elevation, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Settlement Layout - {burg['name']}")
        self.resize(500, 500)
        self.burg = burg
        self.cell_elevation = cell_elevation

        self.burg_gen = BurgGenerator()
        self.layout_data = self.burg_gen.generate_settlement_layout(
            burg["cell_idx"], burg["population"], cell_elevation
        )

        self.layout = QVBoxLayout(self)
        self.lbl_info = QLabel(f"<b>{burg['name']}</b> (Pop: {burg['population']}k, Grid: {burg['cell_idx']})")
        self.layout.addWidget(self.lbl_info)

        self.canvas = QWidget()
        self.canvas.setMinimumSize(400, 400)
        self.canvas.paintEvent = self.draw_map
        self.layout.addWidget(self.canvas)

    def draw_map(self, event):
        painter = QPainter(self.canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.canvas.rect(), QBrush(QColor("#1e1e24")))

        scale_x = self.canvas.width() / 200.0
        scale_y = self.canvas.height() / 200.0

        painter.setPen(QPen(QColor("#2d2d34"), 1))
        painter.setBrush(QBrush(QColor("#7f1d1d") if self.cell_elevation < 20 else QColor("#d97706")))
        for (bx, by, bw, bh) in self.layout_data["blocks"]:
            painter.drawRect(
                int(bx * scale_x), int(by * scale_y),
                int(bw * scale_x), int(bh * scale_y)
            )

        painter.setPen(QPen(QColor("#ffffff") if self.cell_elevation < 20 else QColor("#eab308"), 3))
        for (pt1, pt2) in self.layout_data["streets"]:
            p1 = QPointF(pt1[0] * scale_x, pt1[1] * scale_y)
            p2 = QPointF(pt2[0] * scale_x, pt2[1] * scale_y)
            painter.drawLine(p1, p2)

        painter.setPen(QPen(QColor("#000000"), 2))
        painter.setBrush(QBrush(QColor("#a855f7")))
        cx = self.layout_data["center"][0] * scale_x
        cy = self.layout_data["center"][1] * scale_y
        r  = self.layout_data["plaza_radius"] * scale_x
        painter.drawEllipse(QPointF(cx, cy), r, r)


# =============================================================================
# WIDGET: Custom Relationship Flowchart & Mind-Map Canvas
# =============================================================================
class ModularMindMapCanvas(QWidget):
    """Renders node-based visual charts for character networks and cultural lineages."""
    def __init__(self, node_type="Relationships", parent=None):
        super().__init__(parent)
        self.node_type = node_type
        self.setMinimumSize(300, 200)
        self.nodes = []
        self.connections = []
        self.setStyleSheet("background-color: #0e0e13; border: 1px solid #23232a; border-radius: 6px;")
        self.generate_nodes()

    def generate_nodes(self):
        if self.node_type == "Relationships":
            self.nodes = [
                {"id": 1, "label": "Protagonist", "x": 30, "y": 80},
                {"id": 2, "label": "Rival Group", "x": 180, "y": 30},
                {"id": 3, "label": "Mentor Order", "x": 180, "y": 130}
            ]
            self.connections = [(1, 2, "Enmity"), (1, 3, "Allegiance")]
        else:
            self.nodes = [
                {"id": 1, "label": "Core Culture", "x": 80, "y": 80},
                {"id": 2, "label": "Border Strain", "x": 200, "y": 80}
            ]
            self.connections = [(1, 2, "Linguistic Drift")]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for start_id, end_id, label in self.connections:
            n1 = next(n for n in self.nodes if n["id"] == start_id)
            n2 = next(n for n in self.nodes if n["id"] == end_id)
            pen = QPen(QColor("#04D361") if "Allegiance" in label or "Drift" in label else QColor("#ef4444"), 2)
            painter.setPen(pen)
            painter.drawLine(n1["x"] + 45, n1["y"] + 15, n2["x"] + 45, n2["y"] + 15)
            painter.setPen(QColor("#a0a0c0"))
            painter.drawText(int((n1["x"] + n2["x"])/2), int((n1["y"] + n2["y"])/2) - 5, label)

        for node in self.nodes:
            painter.setPen(QPen(QColor("#04D361"), 1))
            painter.setBrush(QBrush(QColor("#1e1e2e")))
            painter.drawRoundedRect(node["x"], node["y"], 95, 30, 4, 4)
            painter.setPen(QColor("#EEEEF8"))
            painter.drawText(node["x"] + 8, node["y"] + 20, node["label"])


# =============================================================================
# WIDGET: Symmetrical Azgaar-Style Embedded Layer Toolbox
# =============================================================================
class AzgaarMapToolboxWidget(QWidget):
    """Consolidates visual overlays, layer visibilities, and brush options into one workspace component."""
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setStyleSheet("background-color: #13131c; color: #EEEEF8;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # Core operational generation block
        gen_group = QGroupBox("Planetary Operations")
        gen_lay = QVBoxLayout(gen_group)
        btn_regen = QPushButton("🎲 Generate New World Layout")
        btn_regen.clicked.connect(self.main_window.trigger_world_regeneration)
        gen_lay.addWidget(btn_regen)
        layout.addWidget(gen_group)

        # Dynamic brush matrix
        brush_group = QGroupBox("Interactive Canvas Brushes")
        brush_lay = QVBoxLayout(brush_group)
        self.brush_combo = QComboBox()
        self.brush_combo.addItems([
            "Inspect", "Height Paint", "State Paint", "Province Paint", 
            "Culture Paint", "Religion Paint", "River Paint", "Burg Paint", "Magic Paint"
        ])
        self.brush_combo.currentTextChanged.connect(self.main_window.cb_brush_mode.setCurrentText)
        
        slide_lay = QHBoxLayout()
        slide_lay.addWidget(QLabel("Radius:"))
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(1, 4)
        self.radius_slider.valueChanged.connect(self.main_window.change_brush_size)
        slide_lay.addWidget(self.radius_slider)
        
        brush_lay.addWidget(self.brush_combo)
        brush_lay.addLayout(slide_lay)
        layout.addWidget(brush_group)

        # Scrolling layer overlay selectors
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        scroll_content = QWidget()
        scroll_lay = QVBoxLayout(scroll_content)
        scroll_lay.setSpacing(2)

        LAYERS = [
            ("Elevation", "⛰️"), ("Biomes", "🌿"), ("Political States", "🏳️"),
            ("Provinces", "🛡️"), ("Cultures", "🌐"), ("Religions", "✨"),
            ("Magic Layer", "🔮"), ("Production Goods", "📦"), ("Rivers", "🌊"),
            ("Roads", "🛣️"), ("Burgs", "🏰"), ("Underworld & Crime", "🏴☠️")
        ]

        for layer_key, icon in LAYERS:
            row = QWidget()
            row_l = QHBoxLayout(row)
            row_l.setContentsMargins(2, 2, 2, 2)
            lbl = QLabel(f"{icon} {layer_key}")
            chk = QCheckBox()
            chk.setChecked(True)
            chk.stateChanged.connect(lambda state, lk=layer_key: self.main_window._set_layer_visibility(lk, state == 2))
            
            row_l.addWidget(lbl, 1)
            row_l.addWidget(chk)
            scroll_lay.addWidget(row)

        scroll_lay.addStretch()
        scroll_content.setLayout(scroll_lay)
        scroll.setWidget(scroll_content)
        layout.addWidget(QLabel("<b>Layer Visibility Maps:</b>"))
        layout.addWidget(scroll, 1)


# =============================================================================
# WIDGET: Full Azgaar FMG Dedicated Sub-Windows Manager Suite
# =============================================================================
class FullAzgaarSubsystemsWorkspace(QWidget):
    """Implements dedicated full-grid spreadsheet configuration panels for all map elements."""
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.db_path = main_window.db_path
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)

        self.tabs = QTabWidget()
        self.tabs.tabBar().setVisible(False)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #29292E; background: #13131c; }
            QTabBar::tab { background: #16161c; color: #A0A0C0; padding: 4px 8px; border: 1px solid #29292E; font-size: 11px; }
            QTabBar::tab:selected { background: #13131c; color: #04D361; font-weight: bold; }
        """)

        self._init_states_tab()
        self._init_religions_tab()
        self._init_cultures_tab()
        self._init_burgs_tab()
        self._init_provinces_tab()
        self._init_economy_tab()
        self._init_geography_tab()
        self._init_magic_tab()

        self.layout.addWidget(self.tabs)

    def _init_states_tab(self):
        ws = QWidget(); lay = QVBoxLayout(ws)
        self.states_table = QTableWidget(); self.states_table.setColumnCount(4)
        self.states_table.setHorizontalHeaderLabels(["ID", "State Name", "Color", "Expansionism"])
        self.states_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.states_table)
        
        btn = QPushButton("➕ Add New Sovereign State")
        btn.clicked.connect(self.add_state_row)
        lay.addWidget(btn)
        self.tabs.addTab(ws, "🏳️ States")

    def _init_religions_tab(self):
        ws = QWidget(); lay = QVBoxLayout(ws)
        self.rel_table = QTableWidget(); self.rel_table.setColumnCount(3)
        self.rel_table.setHorizontalHeaderLabels(["ID", "Religion Name", "Supreme Deity"])
        self.rel_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.rel_table)
        self.tabs.addTab(ws, "✨ Religions")

    def _init_cultures_tab(self):
        ws = QWidget(); lay = QVBoxLayout(ws)
        self.cult_table = QTableWidget(); self.cult_table.setColumnCount(3)
        self.cult_table.setHorizontalHeaderLabels(["ID", "Culture Name", "Lang Code"])
        self.cult_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.cult_table)
        
        lay.addWidget(QLabel("<b>Phonetic Language Base Onomastics Generator</b>"))
        hb = QHBoxLayout(); self.blend_out = QLineEdit("Phonetic Drift Label"); btn = QPushButton("🎲 Blend Syllables")
        btn.clicked.connect(lambda: self.blend_out.setText("".join(random.choices(["Thor", "Varn", "Bram", "burg", "fjord"], k=2)).capitalize()))
        hb.addWidget(self.blend_out); hb.addWidget(btn); lay.addLayout(hb)
        
        self.cult_canvas = ModularMindMapCanvas("Cultures")
        lay.addWidget(self.cult_canvas, 1)
        self.tabs.addTab(ws, "🌐 Cultures")

    def _init_burgs_tab(self):
        ws = QWidget(); lay = QVBoxLayout(ws)
        self.burgs_table = QTableWidget(); self.burgs_table.setColumnCount(4)
        self.burgs_table.setHorizontalHeaderLabels(["ID", "Burg Name", "Population (k)", "Actions"])
        self.burgs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.burgs_table)
        self.tabs.addTab(ws, "🏰 Burgs")

    def _init_provinces_tab(self):
        ws = QWidget(); lay = QVBoxLayout(ws)
        self.prov_table = QTableWidget(); self.prov_table.setColumnCount(3)
        self.prov_table.setHorizontalHeaderLabels(["ID", "Province Name", "State ID"])
        self.prov_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.prov_table)
        self.tabs.addTab(ws, "🛡️ Provinces")

    def _init_economy_tab(self):
        ws = QWidget(); lay = QVBoxLayout(ws)
        self.econ_list = QListWidget()
        self.econ_list.addItems(["Node 104: Timber Hub [Market Value: 1.2x]", "Node 512: Iron Ore Outpost [Market Value: 2.5x]"])
        lay.addWidget(QLabel("<b>Production Goods &amp; Trade Commodities Ledger</b>"))
        lay.addWidget(self.econ_list)
        self.tabs.addTab(ws, "📦 Economy")

    def _init_geography_tab(self):
        ws = QWidget(); lay = QVBoxLayout(ws)
        self.geo_info = QListWidget()
        self.geo_info.addItems(["Total Continents Formed: 2 meshes", "Tectonic Stress Hotspots: Grey Triangles Active Peaks"])
        lay.addWidget(QLabel("<b>Planetary Tectonic Plates Properties</b>"))
        lay.addWidget(self.geo_info)
        self.tabs.addTab(ws, "⛰️ Geography")

    def _init_magic_tab(self):
        ws = QWidget(); lay = QVBoxLayout(ws)
        self.magic_list = QListWidget()
        self.magic_list.addItems(["Leyline Conjunction 45: Wild Magic Infused Dust", "Leyline Conjunction 82: Aether Storm Cell Zone"])
        lay.addWidget(QLabel("<b>Arcane Pollution Layer Registry</b>"))
        lay.addWidget(self.magic_list)
        self.tabs.addTab(ws, "🔮 Magic")

    def refresh_all_grids(self):
        """Loads live datasets straight from SQLite rows to match Azgaar spreadsheet data metrics."""
        self.states_table.blockSignals(True); self.states_table.setRowCount(0)
        self.rel_table.blockSignals(True); self.rel_table.setRowCount(0)
        self.cult_table.blockSignals(True); self.cult_table.setRowCount(0)
        self.burgs_table.blockSignals(True); self.burgs_table.setRowCount(0)
        self.prov_table.blockSignals(True); self.prov_table.setRowCount(0)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Populate States
            cursor.execute("SELECT id, name, color, expansionism_rate FROM factions")
            f_rows = cursor.fetchall()
            self.states_table.setRowCount(len(f_rows))
            for r_idx, (fid, name, color, expand) in enumerate(f_rows):
                self.states_table.setItem(r_idx, 0, QTableWidgetItem(str(fid)))
                self.states_table.setItem(r_idx, 1, QTableWidgetItem(str(name)))
                self.states_table.setItem(r_idx, 2, QTableWidgetItem(str(color)))
                self.states_table.setItem(r_idx, 3, QTableWidgetItem(str(expand if expand else 1.0)))
                
            # Populate Religions
            cursor.execute("SELECT id, name, supreme_deity FROM religions")
            r_rows = cursor.fetchall()
            self.rel_table.setRowCount(len(r_rows))
            for r_idx, (rid, name, deity) in enumerate(r_rows):
                self.rel_table.setItem(r_idx, 0, QTableWidgetItem(str(rid)))
                self.rel_table.setItem(r_idx, 1, QTableWidgetItem(str(name)))
                self.rel_table.setItem(r_idx, 2, QTableWidgetItem(str(deity if deity else "Unknown")))

            # Populate Cultures
            cursor.execute("SELECT id, name, code FROM cultures")
            c_rows = cursor.fetchall()
            self.cult_table.setRowCount(len(c_rows))
            for r_idx, (cid, name, code) in enumerate(c_rows):
                self.cult_table.setItem(r_idx, 0, QTableWidgetItem(str(cid)))
                self.cult_table.setItem(r_idx, 1, QTableWidgetItem(str(name)))
                self.cult_table.setItem(r_idx, 2, QTableWidgetItem(str(code if code else "C0")))

            # Populate Burgs
            burgs = self.main_window.map_engine.burgs
            self.burgs_table.setRowCount(len(burgs))
            for r_idx, b in enumerate(burgs):
                self.burgs_table.setItem(r_idx, 0, QTableWidgetItem(str(b.get("id", r_idx))))
                self.burgs_table.setItem(r_idx, 1, QTableWidgetItem(str(b.get("name", "Town"))))
                self.burgs_table.setItem(r_idx, 2, QTableWidgetItem(str(b.get("population", 10))))
                
                btn_layout = QPushButton("🗺️ Layout")
                btn_layout.clicked.connect(lambda _, burg_obj=b: BurgMapDialog(burg_obj, 50, self.main_window).exec())
                self.burgs_table.setCellWidget(r_idx, 3, btn_layout)

            # Populate Provinces
            cursor.execute("SELECT id, name, state_id FROM provinces")
            p_rows = cursor.fetchall()
            self.prov_table.setRowCount(len(p_rows))
            for r_idx, (pid, name, sid) in enumerate(p_rows):
                self.prov_table.setItem(r_idx, 0, QTableWidgetItem(str(pid)))
                self.prov_table.setItem(r_idx, 1, QTableWidgetItem(str(name)))
                self.prov_table.setItem(r_idx, 2, QTableWidgetItem(str(sid)))

            conn.close()
        except Exception as e:
            print(f"Spreadsheet auto-sync bypass message: {e}")
            
        self.states_table.blockSignals(False); self.rel_table.blockSignals(False)
        self.cult_table.blockSignals(False); self.burgs_table.blockSignals(False); self.prov_table.blockSignals(False)

    def add_state_row(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        nid = random.randint(100, 9999)
        hex_color = f"#{random.randint(0, 0xFFFFFF):06x}"
        cursor.execute("INSERT INTO factions (id, name, color, expansionism_rate) VALUES (?, ?, ?, 1.0)",
                       (nid, f"Kingdom of NewState_{nid}", hex_color))
        conn.commit()
        conn.close()
        self.refresh_all_grids()
        self.main_window.map_viewer.update()


# =============================================================================
# MAIN WINDOW: LORDSMITH SANDBOX DUAL-BAY PLATFORM
# =============================================================================
class WorldsmithMainWindow(QMainWindow):

    def __init__(self, project_dir):
        super().__init__()
        self.project_dir = os.path.abspath(project_dir)
        project_name = os.path.basename(self.project_dir)
        self.setWindowTitle(f"Lordsmith Studio Workspace - {project_name}")
        self.resize(1650, 950)
        self.setStyleSheet("background: #111116; color: #EEEEF8;")
        self.start_ollama_server()

        # Data paths maps definitions
        self.db_path = os.path.join(self.project_dir, "lore_forge_world.db")
        self.ai_worker    = None
        self.audit_worker = None
        self.selected_cell_idx = None
        self.template_mgr = TemplateManager(self.db_path)
        self.emblem_gen   = EmblemGenerator()

        self.custom_year_length = 420
        self.custom_seasons     = ["Sowing-Time", "High-Sun", "Gold-Leaf", "Deep-Frost"]
        self.cosmos_engine      = CosmosEngine(self.custom_year_length, self.custom_seasons)
        self.map_engine = AzgaarEngine()
        self._session_msg_count = 0

        self._apply_stylesheet()
        self._build_top_windows_menu()

        # --- Compatibility Placeholder Hidden Slots ---
        self.cb_layer = QComboBox(self); self.cb_layer.hide()
        self.chk_layer_visibility = QCheckBox(self); self.chk_layer_visibility.hide()
        self.cb_brush_mode = QComboBox(self)
        self.cb_brush_mode.addItems(["Inspect", "Height Paint", "State Paint", "Province Paint", "Culture Paint", "Religion Paint", "River Paint", "Burg Paint", "Magic Paint"])
        self.cb_brush_mode.currentTextChanged.connect(self.change_brush_mode)
        self.cb_brush_mode.hide()
        self.cb_magic_brush = QComboBox(self); self.cb_magic_brush.hide()
        self.cb_edit_element = QComboBox(self); self.cb_edit_element.hide()
        self.cb_tools = QComboBox(self); self.cb_tools.hide()

        # --- Symmetrical Flanking Splits Framework ---
        self.master_layout = QHBoxLayout()
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.setSpacing(0)
        
        # Left Collapsible File Vault Browser
        self.file_browser_sidebar = QWidget()
        self.file_browser_sidebar.setObjectName("FileTreePanel")
        self.file_browser_sidebar.setFixedWidth(220)
        fb_layout = QVBoxLayout(self.file_browser_sidebar)
        fb_layout.setContentsMargins(6, 6, 6, 6)
        
        self.file_model = QFileSystemModel()
        lore_dir = self.get_lore_dir()
        if not os.path.exists(lore_dir): os.makedirs(lore_dir)
        self.file_model.setRootPath(lore_dir)
        
        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(self.file_model.index(lore_dir))
        self.file_tree.setColumnHidden(1, True)
        self.file_tree.setColumnHidden(2, True)
        self.file_tree.setColumnHidden(3, True)
        self.file_tree.setHeaderHidden(True)
        self.file_tree.clicked.connect(self.on_file_tree_clicked)
        
        fb_layout.addWidget(QLabel("<b>Lore Vault Browser</b>"))
        fb_layout.addWidget(self.file_tree)
        self.master_layout.addWidget(self.file_browser_sidebar)

        # Main splitter workspace container row
        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter.setStyleSheet("QSplitter::handle { background: #29292E; width: 3px; }")
        self.master_layout.addWidget(self.workspace_splitter, 1)

        self._init_modular_tool_pool()

        # PANEL 1: LEFT VIEWPORT OPTIONS SELECTOR (Twelve Core Targets)
        self.left_tool_bay = QWidget()
        self.left_tool_bay_layout = QVBoxLayout(self.left_tool_bay)
        self.left_tool_bay_layout.setContentsMargins(4, 4, 4, 4)
        
        self.left_picker = QComboBox()
        self.left_picker.addItems([
            "Map Layer Canvas View", "States &amp; Countries Table", "Provinces Registry", 
            "Religions Matrix", "Cultures &amp; Languages", "Standing Military Units", 
            "Economic Commodities", "Ecology &amp; Biomes", "Burgs &amp; Settlements", 
            "Geography Tectonics", "Magic Leylines Layer", "Markers Directory"
        ])
        self.left_picker.currentTextChanged.connect(self.handle_left_bay_routing)
        
        self.left_tool_container = QWidget()
        self.left_tool_container_layout = QVBoxLayout(self.left_tool_container)
        self.left_tool_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.left_tool_bay_layout.addWidget(QLabel("<b>Left Focus Panel Target:</b>"))
        self.left_tool_bay_layout.addWidget(self.left_picker)
        self.left_tool_bay_layout.addWidget(self.left_tool_container, 1)
        
        # PANEL 3: RIGHT ADAPTIVE TWIN FRAME (Updates Contextually)
        self.right_tool_bay = QWidget()
        self.right_tool_bay_layout = QVBoxLayout(self.right_tool_bay)
        self.right_tool_bay_layout.setContentsMargins(4, 4, 4, 4)
        
        self.right_tool_container = QWidget()
        self.right_tool_container_layout = QVBoxLayout(self.right_tool_container)
        self.right_tool_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.right_tool_bay_layout.addWidget(QLabel("<b>Right Contextual Twin Controls:</b>"))
        self.right_tool_bay_layout.addWidget(self.right_tool_container, 1)

        # PANEL 2: CENTER FIXED WRITING CANVAS SHEET
        self._build_writing_panel()

        self.workspace_splitter.addWidget(self.left_tool_bay)
        self.workspace_splitter.addWidget(self.note_container) # Main document editor locked in center
        self.workspace_splitter.addWidget(self.right_tool_bay)

        self.left_picker.setCurrentText("Map Layer Canvas View")
        self.handle_left_bay_routing("Map Layer Canvas View")
        
        central_widget = QWidget()
        central_widget.setLayout(self.master_layout)
        self.setCentralWidget(central_widget)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Lordsmith Studio Engine Loaded.")

        self.setup_markers_db()
        self.setup_magic_db()
        self.setup_timeline_db()
        self.setup_staging_db()

        self.active_prompt_timer = QTimer(self)
        self.active_prompt_timer.timeout.connect(self.trigger_global_active_prompt)
        self.active_prompt_timer.start(120000)
        
        self.load_unresolved_inconsistencies()
        self.refresh_note_list()
        self.trigger_welcome_prompt()

    def _build_top_windows_menu(self):
        """Classic top horizontal application drop-down menu bar integration."""
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File Workspace")
        file_menu.addAction("🎲 Procedural New World Layout", self.trigger_world_regeneration)
        file_menu.addAction("📂 Open Database Workspace (.db)", self.load_world_from_file)
        file_menu.addAction("💾 Save Database Workspace (.db)", self.save_world_to_file)
        file_menu.addSeparator()
        file_menu.addAction("Exit System", self.close)

        import_menu = menu_bar.addMenu("&Imports")
        import_menu.addAction("📄 Import Single Note", self.import_external_note)
        import_menu.addAction("📁 Ingest Note Directory Folder", self.import_external_folder)

    def _init_modular_tool_pool(self):
        """Pre-pools and maps widgets into separate tracking frames to allow dynamic flanking swaps."""
        # Left Viewport Frame Layers
        self.map_canvas_viewport_layer = QWidget()
        mv_lay = QVBoxLayout(self.map_canvas_viewport_layer)
        mv_lay.setContentsMargins(0, 0, 0, 0)
        self.map_viewer = MapViewerWidget(self)
        self.map_viewer.cell_hovered.connect(self.handle_cell_hovered)
        self.map_viewer.cell_clicked.connect(self.handle_cell_clicked)
        mv_lay.addWidget(self.map_viewer)

        self.timeline_cosmology_viewport_layer = QWidget()
        tl_lay = QVBoxLayout(self.timeline_cosmology_viewport_layer)
        self.celestial_widget = CelestialPreviewWidget(self)
        self.celestial_widget.setFixedHeight(220)
        tl_lay.addWidget(QLabel("<b>Planetary Celestial Orbit Configurations:</b>"))
        tl_lay.addWidget(self.celestial_widget)
        tl_lay.addStretch()

        # Full-Featured Dataset Manager Suite
        self.azgaar_spreadsheet_suite_layer = FullAzgaarSubsystemsWorkspace(self)

        # Right Twin Options Pools
        self.azgaar_brush_toolbox_right = AzgaarMapToolboxWidget(self)
        self.ai_workflow_terminal_right = QWidget()
        self._assemble_modular_ai_panel(self.ai_workflow_terminal_right)
        
        self.timeline_sliders_right = QWidget()
        tsr_lay = QVBoxLayout(self.timeline_sliders_right)
        self.lbl_timeline = QLabel("<b>Historical World Progression Years:</b>")
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setRange(1, 1000 * 420)
        self.timeline_slider.valueChanged.connect(self.handle_timeline_changed)
        btn_snap = QPushButton("💾 Capture Map Snapshot State")
        btn_snap.clicked.connect(self.save_map_snapshot)
        tsr_lay.addWidget(self.lbl_timeline)
        tsr_lay.addWidget(self.timeline_slider)
        tsr_lay.addWidget(btn_snap)
        tsr_lay.addStretch()

    def handle_left_bay_routing(self, selected_pane_text):
        """
        Dual-Bay Reactive Router.
        Maps the 12 explicit left pane layout requests into full grid data views,
        while adjusting the right twin frame to surface matching contextual controls.
        """
        # Clear Left Bay Container
        left_layout = self.left_tool_container_layout
        while left_layout.count():
            item = left_layout.takeAt(0)
            w = item.widget()
            if w: w.setParent(None)

        # Clear Right Bay Twin Container
        right_layout = self.right_tool_container_layout
        while right_layout.count():
            item = right_layout.takeAt(0)
            w = item.widget()
            if w: w.setParent(None)

        # Route matching operations couples
        if selected_pane_text == "Map Layer Canvas View":
            left_layout.addWidget(self.map_canvas_viewport_layer)
            self.map_canvas_viewport_layer.show()
            
            # Map View docks the Brush layout toolbox on the right
            right_layout.addWidget(self.azgaar_brush_toolbox_right)
            self.azgaar_brush_toolbox_right.show()

        elif selected_pane_text == "Markers Directory":
            left_layout.addWidget(self.timeline_cosmology_viewport_layer)
            self.timeline_cosmology_viewport_layer.show()
            
            # Markers/Cosmology view couples to the chronological year progression sliders
            right_layout.addWidget(self.timeline_sliders_right)
            self.timeline_sliders_right.show()

        else:
            # Map all individual Azgaar FMG full data management panels
            left_layout.addWidget(self.azgaar_spreadsheet_suite_layer)
            self.azgaar_spreadsheet_suite_layer.show()
            
            # Spreadsheet views couple to the background AI lore terminal audit logs on the right
            right_layout.addWidget(self.ai_workflow_terminal_right)
            self.ai_workflow_terminal_right.show()

            # Shift dynamic spreadsheets tab indices natively to match choices
            tab_index_map = {
                "States &amp; Countries Table": 0, "Religions Matrix": 1, "Cultures &amp; Languages": 2,
                "Burgs &amp; Settlements": 3, "Provinces Registry": 4, "Economic Commodities": 5,
                "Geography Tectonics": 6, "Magic Leylines Layer": 7
            }
            target_idx = tab_index_map.get(selected_pane_text, 0)
            self.azgaar_spreadsheet_suite_layer.tabs.setCurrentIndex(target_idx)
            self.azgaar_spreadsheet_suite_layer.refresh_all_grids()

        self.workspace_splitter.refresh()

    def start_ollama_server(self):
        import subprocess
        import urllib.request
        try:
            req = urllib.request.Request("http://localhost:11434/")
            with urllib.request.urlopen(req, timeout=1) as response:
                if response.status == 200: return
        except:
            pass
        try:
            subprocess.Popen(["ollama", "serve"], creationflags=0x08000000, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Failed to auto-launch Ollama: {e}")

    def _apply_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #111116; color: #E1E1E6; font-family: Arial, sans-serif; font-size: 13px; }
            QSplitter::handle { background: #29292E; width: 3px; }
            QTableWidget { background-color: #1a1a24; gridline-color: #29292E; color: #E1E1E6; }
            QHeaderView::section { background-color: #111116; color: #A0A0C0; font-weight: bold; border: none; }
            QPushButton, QComboBox { background: #202028; border: 1px solid #29292E; color: #E1E1E6; border-radius: 4px; padding: 4px 8px; font-weight: bold; }
            QPushButton:hover, QComboBox:hover { background: #29292E; border-color: #04D361; }
            QGroupBox { border: 1px solid #29292E; border-radius: 6px; margin-top: 8px; padding-top: 8px; font-weight: bold; color: #04D361; }
        """)

    def _build_writing_panel(self):
        self.note_container = QWidget(); note_layout = QVBoxLayout(self.note_container)
        note_layout.setContentsMargins(0, 0, 0, 0); note_layout.setSpacing(0)
        toolbar = QWidget(); toolbar.setFixedHeight(42); toolbar_l = QHBoxLayout(toolbar)
        
        self.btn_save_note = QToolButton(); self.btn_save_note.setText("Save"); self.btn_save_note.clicked.connect(self.save_current_note)
        self.btn_bind_map = QToolButton(); self.btn_bind_map.setText("Pin"); self.btn_bind_map.clicked.connect(self.bind_note_to_map_cell)
        toolbar_l.addWidget(self.btn_save_note); toolbar_l.addWidget(self.btn_bind_map); toolbar_l.addStretch()
        note_layout.addWidget(toolbar)

        title_lay = QHBoxLayout(); title_lay.setContentsMargins(8, 4, 8, 4)
        self.note_title_input = QLineEdit(); self.note_title_input.setPlaceholderText("Note Document Title...")
        btn_bind_dialog = QPushButton("📌 Bind to Map Element"); btn_bind_dialog.clicked.connect(self.open_bind_dialog)
        title_lay.addWidget(self.note_title_input, 1); title_lay.addWidget(btn_bind_dialog)
        note_layout.addLayout(title_lay)

        self.note_editor = MarkdownNotebookEditor(self)
        self.note_editor.tag_detected.connect(self.handle_tag_found)
        self.note_editor.link_clicked.connect(self.handle_link_clicked)
        note_layout.addWidget(self.note_editor, 1)

        self.staging_action_widget = QWidget(); self.staging_action_widget.setVisible(False)

    def _assemble_modular_ai_panel(self, parent_widget):
        ai_layout = QVBoxLayout(parent_widget); ai_layout.setContentsMargins(0, 0, 0, 0); ai_layout.setSpacing(4)
        self.ai_prompt_history = QTextEdit(); self.ai_prompt_history.setReadOnly(True)
        ai_layout.addWidget(self.ai_prompt_history, 1)
        
        inp_lay = QHBoxLayout(); self.ai_input = QLineEdit(); self.ai_input.returnPressed.connect(self.send_ai_prompt)
        btn_send = QPushButton(">"); btn_send.clicked.connect(self.send_ai_prompt)
        inp_lay.addWidget(self.ai_input, 1); inp_lay.addWidget(btn_send)
        ai_layout.addLayout(inp_lay)

        self.inconsistency_list = QListWidget(); self.inconsistency_list.setFixedHeight(60)
        ai_layout.addWidget(QLabel("⚠️ Active Lore Contradictions:"))
        ai_layout.addWidget(self.inconsistency_list)

    def _open_layer_editor(self, layer_key):
        pass

    def _select_layer_row(self, layer_key):
        self.cb_layer.setCurrentText(layer_key)

    def _set_layer_visibility(self, layer_key, visible):
        self.map_viewer.visibility_map[layer_key] = visible
        self.map_viewer.update()

    def change_brush_size(self, val):
        self.map_viewer.brush_size = val

    def open_element_table_editor(self, val):
        pass

    def change_brush_mode(self, brush_name):
        self.map_viewer.brush_mode = brush_name

    def load_world_from_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Load Workspace", "", "Databases (*.db)")
        if f:
            import shutil; shutil.copy(f, self.db_path)
            self.trigger_world_regeneration()

    def save_world_to_file(self):
        f, _ = QFileDialog.getSaveFileName(self, "Save Workspace", "", "Databases (*.db)")
        if f: import shutil; shutil.copy(self.db_path, f)

    def get_lore_dir(self):
        return os.path.join(self.project_dir, "lore")

    def trigger_world_regeneration(self):
        self.statusBar.showMessage("Re-simulating full multi-layered world layout geometry...")
        try:
            self.map_engine.generate_voronoi_mesh()
            self.map_engine.run_heightmap_pipeline()
            self.map_engine.run_hydrology_rivers()
            self.map_engine.run_biomes_climate(wind_angle_deg=45)
            self.map_engine.run_cultures_generation()
            self.map_engine.run_states_expansion()
            self.map_engine.slice_state_provinces()
            self.map_engine.run_diplomacy_matrix_engine()
            self.map_engine.run_religions_generation()
            self.map_engine.run_burgs_generation()
            self.map_engine.run_roads_pathfinding()
            self.map_engine.run_trade_and_market_simulation()
            self.map_engine.run_military_generator()
            self.map_engine.run_production_goods()
            self.map_engine.sink_generated_world_to_db(self.db_path)
            self.load_map_data_to_viewer()
            self.statusBar.showMessage("Planetary layers updated successfully.")
        except Exception as e:
            print(f"Simulation failed: {e}")

    def load_unresolved_inconsistencies(self):
        self.inconsistency_list.clear()
        try:
            conn = sqlite3.connect(self.db_path); cur = conn.cursor()
            cur.execute("SELECT description FROM inconsistencies WHERE status='Active'")
            for r in cur.fetchall(): self.inconsistency_list.addItem(r[0])
            conn.close()
        except: pass

    def handle_inconsistency_double_clicked(self, item):
        self.ai_input.setText(f"Help me reconcile this lore error: {item.text()}")

    def setup_markers_db(self):
        try:
            conn = sqlite3.connect(self.db_path); cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS note_map_bindings (note_id INTEGER, cell_idx INTEGER UNIQUE)")
            cursor.execute("CREATE TABLE IF NOT EXISTS markdown_map_bindings (title TEXT PRIMARY KEY, bind_type TEXT, bind_target TEXT, cell_idx INTEGER)")
            cursor.execute("CREATE TABLE IF NOT EXISTS multi_dimensional_coordinates (id TEXT PRIMARY KEY, title TEXT, bind_type TEXT, cell_idx INTEGER, dimension_z TEXT, custom_properties TEXT)")
            conn.commit(); conn.close()
        except Exception as e: print(e)

    def setup_timeline_db(self):
        try:
            conn = sqlite3.connect(self.db_path); cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS map_snapshots (year INTEGER PRIMARY KEY, engine_state_json BLOB)")
            cursor.execute("CREATE TABLE IF NOT EXISTS timeline_notes (id INTEGER PRIMARY KEY, year INTEGER, title TEXT, content TEXT)")
            conn.commit(); conn.close()
        except Exception as e: print(e)

    def setup_staging_db(self):
        try:
            conn = sqlite3.connect(self.db_path); cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, title TEXT, content TEXT)")
            cursor.execute("CREATE TABLE IF NOT EXISTS lore_drafts (id INTEGER PRIMARY KEY, title TEXT, content TEXT)")
            cursor.execute("CREATE TABLE IF NOT EXISTS note_history (id INTEGER PRIMARY KEY, note_id INTEGER, title TEXT, content TEXT)")
            conn.commit(); conn.close()
        except Exception as e: print(e)

    def setup_magic_db(self):
        try:
            conn = sqlite3.connect(self.db_path); cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS magic_layers (cell_idx INTEGER PRIMARY KEY, magic_type TEXT NOT NULL)")
            conn.commit(); conn.close()
        except: pass

    def import_external_note(self):
        f, _ = QFileDialog.getOpenFileName(self, "Import Note", "", "Markdown (*.md);;Text (*.txt)")
        if f: self.start_ingestion([f])

    def import_external_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Import Notes Folder")
        if d:
            fl = [os.path.join(d, filename) for filename in os.listdir(d) if filename.endswith(('.md', '.txt'))]
            if fl: self.start_ingestion(fl)

    def start_ingestion(self, file_list):
        self.ingestor_worker = AILoreIngestor(file_list, self.db_path, self.get_lore_dir(), genre="Fantasy")
        self.ingestor_worker.progress_update.connect(lambda current, total, f: self.statusBar.showMessage(f"Ingesting {current}/{total}: {f}..."))
        self.ingestor_worker.ingestion_complete.connect(self.handle_ingestion_complete)
        self.ingestor_worker.start()

    def handle_ingestion_complete(self):
        self.statusBar.showMessage("AI Ingestion Complete!")
        if hasattr(self, "lbl_session_progress"):
            self.statusBar.showMessage("AI Ingestion Complete! Note caches synced down completely.")
            return
        self.ai_prompt_history.append("<b>[System]</b> Folder structure organized and parsed into database schemas.")
        self.process_spatial_seeding_from_imported_text()

    def process_spatial_seeding_from_imported_text(self):
        try:
            conn = sqlite3.connect(self.db_path); cursor = conn.cursor()
            cursor.execute("SELECT title, content FROM notes")
            notes = [f"{title}: {content}" for title, content in cursor.fetchall()]
            conn.close()
            combined_notes = "\n".join(notes)
            from python_fmg.core.ai_worker import AISpatialExtractorWorker
            self.spatial_worker = AISpatialExtractorWorker(combined_notes)
            self.spatial_worker.extraction_complete.connect(self.apply_spatial_rules_to_map)
            self.spatial_worker.start()
        except Exception as e: print(e)

    def apply_spatial_rules_to_map(self, rules_json_str):
        self.statusBar.showMessage("Applying extracted spatial constraints to Map...")
        import json
        
        try:
            # Simple cleanup of markdown json block
            clean_str = rules_json_str.strip()
            if clean_str.startswith("```json"):

                clean_str = clean_str[7:]
            if clean_str.startswith("```"):
                clean_str = clean_str[3:]
            if clean_str.endswith("```"):
                clean_str = clean_str[:-3]
                
            rules_list = json.loads(clean_str)
            text_anchors = self.map_engine.solve_spatial_constraints(rules_list)
            
            # Re-run simulation pipeline with text parameters injected
            self.map_engine.generate_voronoi_mesh()
            self.map_engine.run_heightmap_pipeline(text_mined_anchors=text_anchors)
            self.map_engine.run_hydrology_rivers()
            self.map_engine.run_biomes_climate()
            
            # Sync back down to canvas layout
            self.load_map_data_to_viewer()
            self.statusBar.showMessage("Map reverse-engineered from text constraints successfully!")
            
        except Exception as e:
            print(f"Failed to apply spatial constraints: {e}")
            self.statusBar.showMessage("Failed to apply spatial constraints. See console.")

    def handle_driver_prompt(self, filepath, subheading, prompt_text):
        # We store the active prompt context so when the user replies, we can update it
        self.pending_driver_file = filepath
        self.pending_driver_subheading = subheading
        
        filename = os.path.basename(filepath)
        title = os.path.splitext(filename)[0]
        self.ai_prompt_history.append(
            f'<div style="text-align: left; margin: 2px 30px 6px 4px;">'
            f'<span style="display: inline-block; background: #1a1a2c; color: #D8D8EC; '
            f'border-radius: 14px 14px 14px 2px; padding: 7px 13px; font-size: 12px; '
            f'border-left: 3px solid #E63946;">'
            f'<span style="color: #E63946; font-weight: bold;">A</span> <b>[Missing Info in {title}]</b><br/>{prompt_text}'
            f'</span></div>'
        )
        self._update_session_progress()

    def change_magic_brush(self, brush_name):
        self.map_viewer.active_paint_magic = brush_name

    def trigger_global_active_prompt(self):
        if not hasattr(self, "chk_active_prompts") or not self.chk_active_prompts.isChecked():
            return
            
        import time
        if time.time() - getattr(self, "last_prompt_time", 0) < 60:
            return
            
        # Pick a random state or burg to ask about
        import random
        candidates = []
        if self.map_engine.states:
            st = random.choice(self.map_engine.states)
            if st["id"] > 0:
                candidates.append({"type": "State", "id": st["id"], "name": st["name"]})
        if self.map_engine.burgs:
            b = random.choice(self.map_engine.burgs)
            if b["id"] > 0:
                candidates.append({"type": "Burg", "id": b["id"], "name": b["name"]})
                
        if not candidates:
            return
            
        context = random.choice(candidates)
        genre = self.cb_genre.currentText() if hasattr(self, "cb_genre") else "Fantasy"
        
        from python_fmg.core.ai_worker import LorePromptWorker
        self.lore_prompt_worker = LorePromptWorker(context, self.db_path, genre=genre)
        self.lore_prompt_worker.prompt_ready.connect(self.handle_active_prompt_ready)
        self.lore_prompt_worker.start()

    def handle_cell_clicked(self, idx):
        # 1. Check if we are in Marker Placement Mode
        if hasattr(self, "pending_marker_title") and self.pending_marker_title:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO markdown_map_bindings (title, bind_type, bind_target, cell_idx)
                    VALUES (?, 'marker', NULL, ?)
                """, (self.pending_marker_title, idx))
                conn.commit()
                conn.close()
                self.statusBar.showMessage(f"Marker placed for '{self.pending_marker_title}' at Cell {idx}.")
                self.pending_marker_title = None
                self.map_viewer.setCursor(Qt.CursorShape.ArrowCursor)
                self.load_map_data_to_viewer()
                self.map_viewer.update() # trigger repaint to show marker
            except Exception as e:
                print(f"Error saving marker: {e}")
            return
            
        self.handle_cell_painted(idx)
        self.check_active_lore_prompt(idx)
        
        # 2. Check if there's a Note bound to this cell/entity
        self.check_map_note_bindings(idx)

    def check_map_note_bindings(self, idx):
        cell = self.map_engine.cells[idx]
        state_id = cell.get("state", 0)
        burg_id = cell.get("burg", 0)
        rel_id = cell.get("religion", 0)
        cult_id = cell.get("culture", 0)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            linked_titles = set()
            
            # Check markers on this specific cell first
            cursor.execute("SELECT title FROM markdown_map_bindings WHERE bind_type='marker' AND cell_idx=?", (idx,))
            for row in cursor.fetchall():
                linked_titles.add(row[0])
            
            # Check entities belonging to this cell
            targets = []
            if state_id > 0: targets.append(('state', str(state_id)))
            if burg_id > 0: targets.append(('burg', str(burg_id)))
            if rel_id > 0: targets.append(('religion', str(rel_id)))
            if cult_id > 0: targets.append(('culture', str(cult_id)))
            
            if targets:
                query_parts = " OR ".join(["(bind_type=? AND bind_target=?)"] * len(targets))
                params = []
                for t_type, t_val in targets:
                    params.extend([t_type, t_val])
                    
                cursor.execute(f"SELECT title FROM markdown_map_bindings WHERE {query_parts}", params)
                for row in cursor.fetchall():
                    linked_titles.add(row[0])
                    
            conn.close()
            
            if linked_titles:
                menu = QMenu(self)
                menu.setStyleSheet("QMenu { background: #1e1e2c; border: 1px solid #404060; color: #D0D0E0; border-radius: 4px; padding: 4px 0; } QMenu::item { padding: 6px 16px; } QMenu::item:selected { background: #29293a; color: #04D361; }")
                for title in sorted(list(linked_titles)):
                    action = menu.addAction(f"📄 {title}")
                    action.triggered.connect(lambda checked, t=title: self.load_selected_note(t))
                
                from PyQt6.QtGui import QCursor
                menu.exec(QCursor.pos())
                
        except Exception as e:
            print(f"Error checking map bindings: {e}")
    def check_active_lore_prompt(self, idx):
        if not hasattr(self, "chk_active_prompts") or not self.chk_active_prompts.isChecked():
            return
            
        import time
        if time.time() - getattr(self, "last_prompt_time", 0) < 30: # 30s cooldown
            return
            
        cell = self.map_engine.cells[idx]
        context = {"type": "Cell", "id": idx, "biome": cell.get("biome", ""), "name": ""}
        
        if cell.get("state", 0) > 0:
            st = next((s for s in self.map_engine.states if s["id"] == cell["state"]), None)
            if st:
                context = {"type": "State", "id": st["id"], "name": st["name"], "color": st["color"]}
        elif cell.get("burg", 0) > 0:
            b = next((b for b in self.map_engine.burgs if b["id"] == cell["burg"]), None)
            if b:
                context = {"type": "Burg", "id": b["id"], "name": b["name"], "population": b["population"]}
                
        if not context.get("name"):
            return 
            
        genre = self.cb_genre.currentText() if hasattr(self, "cb_genre") else "Fantasy"
        from python_fmg.core.ai_worker import LorePromptWorker
        self.lore_prompt_worker = LorePromptWorker(context, self.db_path, genre=genre)
        self.lore_prompt_worker.prompt_ready.connect(self.handle_active_prompt_ready)
        self.lore_prompt_worker.start()
        
    def handle_active_prompt_ready(self, text):
        import time
        self.last_prompt_time = time.time()
        if text.startswith("[ACTIVE_PROMPT]"):
            # e.g., "[ACTIVE_PROMPT] Oakhaven: Who rules this?"
            parts = text.replace("[ACTIVE_PROMPT]", "").strip().split(":", 1)
            if len(parts) == 2:
                self.pending_active_entity = parts[0].strip()
                text = f"<b>Active Prompt:</b><br/>{parts[1].strip()}"
        self.handle_ai_response(text)

    def handle_cell_painted(self, idx):
        try:
            conn   = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO magic_layers (cell_idx, magic_type)
                VALUES (?, ?)
                ON CONFLICT(cell_idx) DO UPDATE SET magic_type=excluded.magic_type
            """, (idx, self.map_viewer.active_paint_magic))
            conn.commit()
            conn.close()
            self.statusBar.showMessage(f"Painted Cell {idx} with {self.map_viewer.active_paint_magic}.")
        except Exception as e:
            self.statusBar.showMessage(f"Failed to save magic cell: {e}")

    def handle_timeline_changed(self, absolute_day_val):
        year = (absolute_day_val // self.custom_year_length) + 1
        day_of_year = (absolute_day_val % self.custom_year_length)
        if day_of_year == 0:
            day_of_year = self.custom_year_length
            year -= 1

        num_seasons     = len(self.custom_seasons)
        season_duration = self.custom_year_length / num_seasons
        season_idx      = min(int((day_of_year - 1) / season_duration), num_seasons - 1)
        season          = self.custom_seasons[season_idx]

        self.lbl_timeline.setText(f"<b>Historical Timeline (Year {year}, Day {day_of_year} / {season})</b>")
        self.celestial_widget.set_day(day_of_year)

        # Trigger celestial alignment magic flux modifier calculations
        flux_mod = self.cosmos_engine.update_celestial_magic_flux(self.db_path, day_of_year)

        if not hasattr(self, "_last_interpolated_year") or self._last_interpolated_year != year:
            self.interpolate_map_state(year)
            self._last_interpolated_year = year

    def save_map_snapshot(self):
        absolute_day_val = self.timeline_slider.value()
        year = (absolute_day_val // self.custom_year_length) + 1
        state_data = {
            "cells": self.map_engine.cells,
            "burgs": self.map_engine.burgs,
            "states": self.map_engine.states,
            "provinces_pool": self.map_engine.provinces_pool,
            "religions": self.map_engine.religions,
            "cultures": self.map_engine.cultures,
            "military_regiments": self.map_engine.military_regiments if hasattr(self.map_engine, "military_regiments") else []
        }
        try:
            import json
            json_data = json.dumps(state_data)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO map_snapshots (year, engine_state_json) VALUES (?, ?)", (year, json_data))
            conn.commit()
            conn.close()
            self.statusBar.showMessage(f"Map Snapshot saved for Year {year}.")
            QMessageBox.information(self, "Snapshot Saved", f"Successfully captured map state at Year {year}.")
        except Exception as e:
            QMessageBox.critical(self, "Snapshot Error", f"Failed to save snapshot: {e}")


        
    def interpolate_map_state(self, year):
        try:
            import json
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT year, engine_state_json FROM map_snapshots WHERE year <= ? ORDER BY year DESC LIMIT 1", (year,))
            prev_snap = cursor.fetchone()
            
            cursor.execute("SELECT year, engine_state_json FROM map_snapshots WHERE year > ? ORDER BY year ASC LIMIT 1", (year,))
            next_snap = cursor.fetchone()
            
            conn.close()
            
            if not prev_snap and not next_snap:
                return # No snapshots
                
            if not next_snap or not prev_snap or prev_snap[0] == next_snap[0]:
                target = prev_snap if prev_snap else next_snap
                self.load_snapshot_data(json.loads(target[1]))
                return
                
            # Basic interpolation (Snap to nearest temporal snapshot to avoid border fragmentation)
            dist_prev = abs(year - prev_snap[0])
            dist_next = abs(next_snap[0] - year)
            
            if dist_prev <= dist_next:
                target_json = json.loads(prev_snap[1])
            else:
                target_json = json.loads(next_snap[1])
                
            self.load_snapshot_data(target_json)
            self.map_engine.patch_temporal_lifecycles(year)
            self.map_viewer.update()
            
        except Exception as e:
            print(f"Error interpolating: {e}")

    def audit_timeline(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM map_snapshots")
            snap_count = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM timeline_notes")
            note_count = cursor.fetchone()[0]
            conn.close()
            
            if snap_count < 1 and note_count < 1:
                QMessageBox.warning(self, "Audit Failed", "No timeline snapshots or notes exist yet to audit.")
                return
                
            self.statusBar.showMessage("Sending timeline data to AI Lorekeeper for continuity audit...")
            # We would spawn an Ollama AI thread here to analyze notes vs states.
            # For now, append a sample inconsistency.
            import datetime
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inconsistencies (timestamp, title, description, is_resolved)
                VALUES (?, ?, ?, ?)
            """, (datetime.datetime.now().isoformat(), "Timeline Lore Audit", "AI Lorekeeper spotted potential contradiction: Review map state vs notes.", 0))
            conn.commit()
            conn.close()
            
            self.load_unresolved_inconsistencies()
            self.inconsistency_list.setVisible(True)
            QMessageBox.information(self, "Audit Complete", "Timeline has been audited. See Inconsistencies panel for details.")
            
        except Exception as e:
            QMessageBox.critical(self, "Audit Error", f"Failed to audit timeline: {e}")

    def load_snapshot_data(self, data):
        self.map_engine.cells = data.get("cells", self.map_engine.cells)
        self.map_engine.burgs = data.get("burgs", self.map_engine.burgs)
        self.map_engine.states = data.get("states", self.map_engine.states)
        self.map_engine.provinces_pool = data.get("provinces_pool", self.map_engine.provinces_pool)
        self.map_engine.religions = data.get("religions", self.map_engine.religions)
        self.map_engine.cultures = data.get("cultures", self.map_engine.cultures)
        if hasattr(self.map_engine, "military_regiments"):
            self.map_engine.military_regiments = data.get("military_regiments", self.map_engine.military_regiments)
        
        self.load_map_data_to_viewer()
        if hasattr(self, "map_viewer"):
            self.map_viewer.update()
        if flux_mod > 1.0:
            self.statusBar.showMessage(f"Celestial Alignment Active! Magic power multiplier is surged x{flux_mod}.")

    def handle_cell_hovered(self, idx, elev, biome, state):
        self.selected_cell_idx = idx

        bound_note_title = "None"
        try:
            conn   = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT notes.title FROM notes
                JOIN note_map_bindings ON notes.id = note_map_bindings.note_id
                WHERE note_map_bindings.cell_idx = ?
            """, (idx,))
            row = cursor.fetchone()
            if row:
                bound_note_title = row[0]
            conn.close()
        except:
            pass

        troops = 0
        for reg in self.map_engine.military_regiments:
            if reg["cell_idx"] == idx:
                troops = reg["total_troops"]

        cell     = self.map_engine.cells[idx]
        province = f"Province {cell['province']}" if cell["province"] > 0 else "None"
        culture  = f"Culture {cell['culture']}"   if cell["culture"]  > 0 else "None"
        religion = f"Religion {cell['religion']}" if cell["religion"] > 0 else "None"

        self.statusBar.showMessage(
            f"Cell ID: {idx} | Bound Note: {bound_note_title} | State: {state} | "
            f"Prov: {province} | Cult: {culture} | Rel: {religion} | Troops: {troops}"
        )

        # Enable opening of settlement map editor if double-clicking a cell containing a burg
        if cell["burg"] > 0:
            self.statusBar.showMessage(
                f"Settlement detected | Double-click to open street layout map."
            )

    def mouseDoubleClickEvent(self, event):
        if self.selected_cell_idx is not None:
            cell = self.map_engine.cells[self.selected_cell_idx]
            if cell["burg"] > 0:
                burg = next((b for b in self.map_engine.burgs if b["id"] == cell["burg"]), None)
                if burg:
                    dialog = BurgMapDialog(burg, cell["h"], self)
                    dialog.exec()

    def bind_note_to_map_cell(self):
        title = self.note_title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "No Note", "Save or open a note first before binding it to a map cell.")
            return
        if self.selected_cell_idx is None:
            QMessageBox.warning(self, "No Cell Hovered", "Hover over a map cell coordinate before binding.")
            return

        try:
            conn   = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM notes WHERE title=?", (title,))
            row = cursor.fetchone()
            if not row:
                self.save_current_note()
                cursor.execute("SELECT id FROM notes WHERE title=?", (title,))
                row = cursor.fetchone()

            note_id = row[0]

            cursor.execute("""
                INSERT INTO note_map_bindings (note_id, cell_idx)
                VALUES (?, ?)
                ON CONFLICT(cell_idx) DO UPDATE SET note_id=excluded.note_id
            """, (note_id, self.selected_cell_idx))

            conn.commit()
            conn.close()
            self.statusBar.showMessage(
                f"Successfully bound note '{title}' to Cell ID: {self.selected_cell_idx}."
            )
        except Exception as e:
            QMessageBox.critical(self, "Binding Error", f"Failed to bind note: {e}")

    def load_map_data_to_viewer(self):
        try:
            conn   = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT cell_idx, magic_type FROM magic_layers")
            for cell_idx, m_type in cursor.fetchall():
                self.map_viewer.magic_data[cell_idx] = m_type
                
            cursor.execute("SELECT cell_idx, title FROM markdown_map_bindings WHERE bind_type='marker'")
            self.map_viewer.markdown_markers = cursor.fetchall()
            
            conn.close()
        except:
            self.map_viewer.markdown_markers = []

        for cell in self.map_engine.cells:
            cell_idx = cell["i"]
            self.map_viewer.elevation_data[cell_idx] = cell["h"]
            self.map_viewer.biomes_data[cell_idx]    = cell["biome"]

            if cell["state"] > 0:
                color_hex = "#7f1d1d"
                for st in self.map_engine.states:
                    if st["id"] == cell["state"]:
                        color_hex = st["color"]
                self.map_viewer.factions_data[cell_idx] = color_hex
            else:
                self.map_viewer.factions_data[cell_idx] = "#18181b"
        self.map_viewer.update()

    def trigger_welcome_prompt(self):
        welcome_html = (
            '<div style="text-align: left; margin: 8px 4px;">'
            '<span style="display: inline-block; background: #1a1a2c; color: #D0D0E0; '
            'border-radius: 12px 12px 12px 2px; padding: 10px 14px; '
            'border-left: 3px solid #04D361; max-width: 95%;">'
            '<span style="color: #04D361; font-weight: bold;">A </span>'
            '<b>Welcome to Worldsmith Sandbox!</b><br>'
            "I am your analytical AI assistant. Let's start at the beginning - "
            'tell me about your world concept, or ask me to audit your timeline for continuity, '
            'help organize your lore, or point out gaps in your established facts.'
            '</span></div>'
        )
        self.ai_prompt_history.append(welcome_html)

    def change_map_layer(self, layer_name):
        self.map_viewer.layer_mode = layer_name
        # Update hidden visibility checkbox (preserves toggle_layer_visibility slot)
        self.chk_layer_visibility.setChecked(self.map_viewer.visibility_map.get(layer_name, True))
        # Show magic tools section in floating panel when on Magic Layer
        if hasattr(self, "floating_layer_tools"):
            self.floating_layer_tools.magic_section.setVisible(layer_name == "Magic Layer")
        self.map_viewer.update()

    def handle_tag_found(self, tag_name):
        try:
            conn   = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
            conn.commit()
            conn.close()
        except:
            pass

    def refresh_note_list(self):
        pass

    def populate_file_tree(self):
        """Forces the file browser tree to refresh."""
        if hasattr(self, "file_model"):
            lore_dir = self.get_lore_dir()
            if os.path.exists(lore_dir):
                self.file_model.setRootPath(lore_dir)

    def on_file_tree_clicked(self, index):
        file_path = self.file_model.filePath(index)
        if not self.file_model.isDir(index) and (file_path.endswith('.md') or file_path.endswith('.txt')):
            title = os.path.splitext(os.path.basename(file_path))[0]
            # Auto-save current if needed
            if getattr(self, "current_note_file_path", None) or getattr(self, "current_loaded_draft_id", None):
                self.save_current_note()
                
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            self.current_note_file_path = file_path
            self.current_loaded_draft_id = None
            self.staging_action_widget.setVisible(False)
            self.note_title_input.setText(title)
            self.note_editor.setPlainText(content)
            self.statusBar.showMessage(f"Loaded note '{title}' from filesystem.")

    def load_selected_note(self, title):
        # Auto-save the currently open note (if any) before we overwrite the editor
        if getattr(self, "current_note_file_path", None) or getattr(self, "current_loaded_draft_id", None):
            self.save_current_note()

        self.current_loaded_draft_id = None
        self.staging_action_widget.setVisible(False)
        
        if title == "New Note..." or not title:
            self.note_title_input.clear()
            self.note_editor.clear()
            self.current_note_file_path = None
            return

        try:
            if title.startswith("[DRAFT] "):
                clean_title = title.replace("[DRAFT] ", "", 1)
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT id, title, content FROM lore_drafts WHERE title = ?", (clean_title,))
                row = cursor.fetchone()
                if row:
                    self.current_loaded_draft_id = row[0]
                    self.note_title_input.setText(row[1])
                    self.note_editor.setPlainText(row[2])
                    self.current_note_file_path = None
                    self.staging_action_widget.setVisible(True)
                    self.statusBar.showMessage(f"Loaded draft '{clean_title}'.")
                conn.close()
            else:
                # Load from file system
                lore_dir = self.get_lore_dir()
                file_path = os.path.join(lore_dir, f"{title}.md")
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.current_note_file_path = file_path
                    self.note_title_input.setText(title)
                    self.note_editor.setPlainText(content)
                    self.statusBar.showMessage(f"Loaded note '{title}' from filesystem.")
        except Exception as e:
            self.statusBar.showMessage(f"Error loading note: {e}")

    def handle_link_clicked(self, link_title):
        self.load_selected_note(link_title)

    def send_ai_prompt(self):
        user_text = self.ai_input.text().strip()
        if not user_text:
            return

        # Styled chat bubble for user message (right-aligned)
        self.ai_prompt_history.append(
            f'<div style="text-align: right; margin: 6px 4px 2px 30px;">'
            f'<span style="display: inline-block; background: #04D361; color: #000000; '
            f'border-radius: 14px 14px 2px 14px; padding: 7px 13px; font-size: 12px;">'
            f'{user_text}'
            f'</span></div>'
        )
        self.ai_input.clear()

        self.statusBar.showMessage("AI is thinking...")
        self.btn_send_prompt.setEnabled(False)

        system_instr = None
        self.is_saving_lore_note = None
        
        if hasattr(self, "pending_driver_file") and self.pending_driver_file:
            # User is answering an active gap question. Update the file!
            try:
                filepath = self.pending_driver_file
                subheading = self.pending_driver_subheading
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace the first instance of [NEEDS_DETAIL] under this subheading with user's text
                # We can just replace the exact text `[NEEDS_DETAIL]` since the file is targeted.
                content = content.replace('[NEEDS_DETAIL]', f"{user_text.strip()}", 1)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.statusBar.showMessage(f"Updated {os.path.basename(filepath)} with new details.")
                self.populate_file_tree()
                
                # Clear pending and trigger driver again to find the next gap
                self.pending_driver_file = None
                self.pending_driver_subheading = None
                
                genre = self.cb_genre.currentText() if hasattr(self, "cb_genre") else "Fantasy"
                self.driver_worker = AILoreDriverWorker(self.get_lore_dir(), self.db_path, genre=genre)
                self.driver_worker.prompt_ready.connect(self.handle_driver_prompt)
                self.driver_worker.start()
                
                self.btn_send_prompt.setEnabled(True)
                return
            except Exception as e:
                print(f"Error saving detail to file: {e}")
                
        if hasattr(self, "pending_active_entity") and self.pending_active_entity:
            # User is answering the prompt. Save their exact text!
            try:
                import datetime
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                # Check if note exists and append, or create new (in drafts)
                cursor.execute("SELECT id, content FROM lore_drafts WHERE title = ?", (f"{self.pending_active_entity} History",))
                existing = cursor.fetchone()
                if existing:
                    new_content = existing[1] + "\n\n" + user_text.strip()
                    cursor.execute("UPDATE lore_drafts SET content = ? WHERE id = ?", (new_content, existing[0]))
                else:
                    cursor.execute("""
                        INSERT INTO lore_drafts (title, content, created_at, is_ai_generated)
                        VALUES (?, ?, ?, ?)
                    """, (f"{self.pending_active_entity} History", user_text.strip(), datetime.datetime.now().isoformat(), 0))
                conn.commit()
                conn.close()
                self.refresh_staging_area()
                self.statusBar.showMessage(f"Saved draft lore for {self.pending_active_entity} to staging area!")
            except Exception as e:
                print(f"Error saving user lore: {e}")
                
            system_instr = (
                f"The user just expanded the lore for '{self.pending_active_entity}' with this answer: '{user_text}'. "
                f"Ask EXACTLY ONE short, creative follow-up question to push them to expand on it further. "
                f"Keep your response to a single sentence question."
            )
            # Re-set pending entity so the follow-up ALSO gets saved if they reply again!
            # The next response will be handled identically because pending_active_entity is kept intact.
            # We don't clear it here, so the loop continues.
        else:
            self.pending_active_entity = None

        genre = self.cb_genre.currentText() if hasattr(self, "cb_genre") else "Fantasy"
        self.ai_worker = OllamaPromptWorker(user_text, db_path=self.db_path, system_instruction=system_instr, genre=genre)
        self.ai_worker.response_received.connect(self.handle_ai_response)
        self.ai_worker.error_occurred.connect(self.handle_ai_error)
        self.ai_worker.start()

    def handle_ai_response(self, text):

        # Styled chat bubble for AI message (left-aligned)
        self.ai_prompt_history.append(
            f'<div style="text-align: left; margin: 2px 30px 6px 4px;">'
            f'<span style="display: inline-block; background: #1a1a2c; color: #D8D8EC; '
            f'border-radius: 14px 14px 14px 2px; padding: 7px 13px; font-size: 12px; '
            f'border-left: 3px solid #04D361;">'
            f'<span style="color: #04D361; font-weight: bold;">A</span> {text}'
            f'</span></div>'
        )
        self.statusBar.showMessage("Response received.")
        self.btn_send_prompt.setEnabled(True)
        self._update_session_progress()

    def handle_ai_error(self, err_msg):
        if "500" in err_msg:
            friendly_err = f'<b>[Error]</b> Ollama returned an Internal Server Error ({err_msg}). This usually means your machine ran out of memory loading the model, or the model file is corrupt. Try running `ollama run qwen2.5:latest` in your terminal to debug.'
        else:
            friendly_err = f'<b>[Error]</b> Could not reach local Ollama server ({err_msg}). Ensure Ollama is running (ollama serve).'
            
        self.ai_prompt_history.append(
            f'<div style="margin: 4px;">'
            f'<span style="color: #ef4444; font-size: 11px;">'
            f'{friendly_err}'
            f'</span></div>'
        )
        self.statusBar.showMessage("AI communication error.")
        self.btn_send_prompt.setEnabled(True)
    def open_bind_dialog(self):
        title = self.note_title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing Title", "Please provide a title for the note before binding.")
            return
            
        dialog = MapBindingDialog(self.db_path, self.map_engine, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.bind_mode == 'entity':
                # Save to database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO markdown_map_bindings (title, bind_type, bind_target, cell_idx)
                    VALUES (?, ?, ?, NULL)
                """, (title, dialog.bind_type, dialog.bind_target))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Bound to Map", f"Successfully bound note '{title}' to {dialog.bind_type}!")
                
            elif dialog.bind_mode == 'marker':
                self.statusBar.showMessage("Click on the map to place your custom marker.")
                self.map_viewer.setCursor(Qt.CursorShape.CrossCursor)
                self.pending_marker_title = title

    def save_current_note(self):
        title   = self.note_title_input.text().strip()
        content = self.note_editor.toPlainText().strip()

        if not title:
            QMessageBox.warning(self, "Missing Title", "Please provide a title for the note.")
            return

        try:
            file_path = getattr(self, "current_note_file_path", None)
            if not file_path:
                lore_dir = self.get_lore_dir()
                file_path = os.path.join(lore_dir, f"{title}.md")
                self.current_note_file_path = file_path
                
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            self.statusBar.showMessage(f"Note '{title}' saved. Running lore audit...")

            # Trigger asynchronous background lore consistency audit on save
            self.audit_worker = LoreAuditWorker(title, content, db_path=self.db_path)
            self.audit_worker.audit_completed.connect(self.handle_audit_completed)
            self.audit_worker.start()

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save note: {e}")

    def handle_audit_completed(self, contradiction_summary):
        if contradiction_summary:
            warning_text = (
                f"<br><font color='#ef4444'><b>[Lore Audit Inconsistency Detected]:</b></font><br>"
                f"<i>{contradiction_summary}</i><br>"
                f"<font color='#a7f3d0'>This issue has been logged to your anomalies database dashboard.</font><br>"
            )
            self.ai_prompt_history.append(warning_text)
            self.statusBar.showMessage("Inconsistency found and logged!")
            self.load_unresolved_inconsistencies()
        else:
            self.statusBar.showMessage("Lore audit complete. No inconsistencies detected.")

    def compile_static_wiki(self):
        compiler = WikiCompiler(self.db_path)
        success, msg = compiler.compile_wiki()
        if success:
            QMessageBox.information(self, "Wiki Compiled", msg)
        else:
            QMessageBox.critical(self, "Compilation Error", f"Failed to compile wiki: {msg}")

    # =========================================================================
    # LORE STAGING METHODS
    # =========================================================================
    def refresh_staging_area(self):
        self.refresh_note_list()

    def commit_draft(self):
        if not hasattr(self, "current_loaded_draft_id") or not self.current_loaded_draft_id:
            return
        draft_id = self.current_loaded_draft_id
        new_content = self.note_editor.toPlainText().strip()
        
        try:
            import datetime
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT title, is_ai_generated FROM lore_drafts WHERE id = ?", (draft_id,))
            draft_meta = cursor.fetchone()
            if not draft_meta:
                conn.close()
                return
                
            title, is_ai = draft_meta
            
            # Check if main note exists
            cursor.execute("SELECT id, content FROM notes WHERE title = ?", (title,))
            existing = cursor.fetchone()
            
            if existing:
                # Backup to history
                cursor.execute("""
                    INSERT INTO note_history (note_id, title, content, archived_at)
                    VALUES (?, ?, ?, ?)
                """, (existing[0], title, existing[1], datetime.datetime.now().isoformat()))
                
                # Update main note
                cursor.execute("UPDATE notes SET content = ?, updated_at = ? WHERE id = ?", (new_content, datetime.datetime.now().isoformat(), existing[0]))
            else:
                # Insert new main note
                cursor.execute("""
                    INSERT INTO notes (title, content, created_at, updated_at, is_ai_generated)
                    VALUES (?, ?, ?, ?, ?)
                """, (title, new_content, datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat(), is_ai))
            
            # Delete draft
            cursor.execute("DELETE FROM lore_drafts WHERE id = ?", (draft_id,))
            conn.commit()
            conn.close()
            
            self.refresh_note_list()
            self.statusBar.showMessage(f"Committed '{title}' to canonical lore!")
            self.load_selected_note(title) # Switch to the committed note
        except Exception as e:
            QMessageBox.critical(self, "Commit Error", f"Failed to commit lore: {e}")

    def discard_draft(self):
        if not hasattr(self, "current_loaded_draft_id") or not self.current_loaded_draft_id:
            return
        draft_id = self.current_loaded_draft_id
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM lore_drafts WHERE id = ?", (draft_id,))
            conn.commit()
            conn.close()
            self.refresh_note_list()
            self.load_selected_note("New Note...")
            self.statusBar.showMessage("Draft discarded.")
        except Exception as e:
            print(f"Error discarding draft: {e}")


# =============================================================================
# ENTRY POINT
# =============================================================================
def main():
    import subprocess
    try:
        subprocess.Popen(
            ["ollama", "serve"], 
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except FileNotFoundError:
        print("Ollama not found. The AI features will be unavailable.")

    app = QApplication(sys.argv)
    
    from python_fmg.ui.project_wizard import ProjectWizardDialog
    wizard = ProjectWizardDialog()
    if wizard.exec() == QDialog.DialogCode.Accepted and wizard.selected_project_dir:
        window = WorldsmithMainWindow(wizard.selected_project_dir)
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
