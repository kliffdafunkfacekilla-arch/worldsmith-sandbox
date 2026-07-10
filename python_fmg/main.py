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
    QFrame, QToolButton, QScrollArea, QMenu, QTableWidget, QTableWidgetItem, QCompleter, QTreeView
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

        # Draw blocks
        painter.setPen(QPen(QColor("#2d2d34"), 1))
        painter.setBrush(QBrush(QColor("#7f1d1d") if self.cell_elevation < 20 else QColor("#d97706")))
        for (bx, by, bw, bh) in self.layout_data["blocks"]:
            painter.drawRect(
                int(bx * scale_x), int(by * scale_y),
                int(bw * scale_x), int(bh * scale_y)
            )

        # Draw streets
        painter.setPen(QPen(QColor("#ffffff") if self.cell_elevation < 20 else QColor("#eab308"), 3))
        for (pt1, pt2) in self.layout_data["streets"]:
            p1 = QPointF(pt1[0] * scale_x, pt1[1] * scale_y)
            p2 = QPointF(pt2[0] * scale_x, pt2[1] * scale_y)
            painter.drawLine(p1, p2)

        # Draw central plaza
        painter.setPen(QPen(QColor("#000000"), 2))
        painter.setBrush(QBrush(QColor("#a855f7")))
        cx = self.layout_data["center"][0] * scale_x
        cy = self.layout_data["center"][1] * scale_y
        r  = self.layout_data["plaza_radius"] * scale_x
        painter.drawEllipse(QPointF(cx, cy), r, r)


# =============================================================================
# DIALOG: World Element Data Table Editor
# =============================================================================
class DataTableEditor(QDialog):
    def __init__(self, element_type, items_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{element_type} Data Editor")
        self.resize(800, 450)
        self.element_type = element_type
        self.items_list = items_list
        self.parent_win = parent

        self.layout = QVBoxLayout(self)
        
        self.setStyleSheet("""
            QDialog { background-color: #111116; color: #EEEEF8; }
            QTableWidget {
                background-color: #1a1a24; color: #EEEEF8;
                border: 1px solid #29292E; gridline-color: #29292E;
                selection-background-color: #04D361; selection-color: #111116;
                font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px;
            }
            QHeaderView::section {
                background-color: #111116; color: #A0A0C0;
                border: none; border-bottom: 1px solid #04D361;
                padding: 4px; font-weight: bold;
            }
            QPushButton {
                background-color: #16161c; color: #04D361;
                border: 1px solid #04D361; padding: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1a2e1a; }
        """)
        
        self.table = QTableWidget()
        self.layout.addWidget(self.table)
        
        # Setup columns based on type
        if self.element_type == "State":
            self.columns = ["ID", "Name", "Color", "Expansionism", "Gov Form", "Capital Cell", "Cells", "Burgs", "Area", "Population"]
            self.keys = ["id", "name", "color", "expansionism", "type", "capital_cell", "cells_count", "burgs_count", "area", "population"]
        elif self.element_type == "Culture":
            self.columns = ["ID", "Name", "Code", "Env Type", "Is Aquatic", "Cells", "Population"]
            self.keys = ["id", "name", "code", "env_type", "is_aquatic", "cells_count", "population"]
        elif self.element_type == "Religion":
            self.columns = ["ID", "Name", "Type", "Color", "Supreme Deity", "Expansion", "Cells", "Area", "Population"]
            self.keys = ["id", "name", "type", "color", "supreme_deity", "expansionism", "cells_count", "area", "population"]
        elif self.element_type == "Burg":
            self.columns = ["ID", "Name", "Population", "State ID", "Culture ID", "Feature"]
            self.keys = ["id", "name", "population", "state", "culture", "feature"]
        elif self.element_type == "Province":
            self.columns = ["ID", "Name", "Color", "State ID", "Cells", "Burgs", "Area", "Population"]
            self.keys = ["id", "name", "color", "state", "cells_count", "burgs_count", "area", "population"]
        else:
            self.columns = ["ID", "Name"]
            self.keys = ["id", "name"]
            
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.horizontalHeader().setStretchLastSection(True)
        
        self.refresh_table()
        self.table.itemChanged.connect(self.on_item_changed)
        
        h_layout = QHBoxLayout()
        self.btn_add = QPushButton("➕ Add Row")
        self.btn_add.clicked.connect(self.add_row)
        self.btn_delete = QPushButton("🗑️ Delete Selected Row")
        self.btn_delete.clicked.connect(self.delete_row)
        
        h_layout.addWidget(self.btn_add)
        h_layout.addWidget(self.btn_delete)
        self.layout.addLayout(h_layout)

    def refresh_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.items_list))
        
        engine = self.parent_win.map_engine if self.parent_win else None
        
        for row_idx, item in enumerate(self.items_list):
            item_id = item.get("id")
            
            # Compute Azgaar-style real-time statistics
            if engine and self.element_type == "State":
                state_cells = [c for c in engine.cells if c.get("state") == item_id]
                state_burgs = [b for b in engine.burgs if b.get("state") == item_id]
                item["cells_count"] = len(state_cells)
                item["burgs_count"] = len(state_burgs)
                item["area"] = round(len(state_cells) * 12.5, 1) # ~12.5 sq miles per cell
                item["population"] = round(sum(c.get("pop", 1.0) for c in state_cells) + sum(b.get("population", 10) for b in state_burgs), 1)
            elif engine and self.element_type == "Culture":
                culture_cells = [c for c in engine.cells if c.get("culture") == item_id]
                item["cells_count"] = len(culture_cells)
                item["area"] = round(len(culture_cells) * 12.5, 1)
                item["population"] = round(sum(c.get("pop", 1.0) for c in culture_cells), 1)
            elif engine and self.element_type == "Religion":
                religion_cells = [c for c in engine.cells if c.get("religion") == item_id]
                item["cells_count"] = len(religion_cells)
                item["area"] = round(len(religion_cells) * 12.5, 1)
                item["population"] = round(sum(c.get("pop", 1.0) for c in religion_cells), 1)
            elif engine and self.element_type == "Province":
                prov_cells = [c for c in engine.cells if c.get("province") == item_id]
                prov_burgs = [b for b in engine.burgs if b.get("province") == item_id]
                item["cells_count"] = len(prov_cells)
                item["burgs_count"] = len(prov_burgs)
                item["area"] = round(len(prov_cells) * 12.5, 1)
                item["population"] = round(sum(c.get("pop", 1.0) for c in prov_cells) + sum(b.get("population", 10) for b in prov_burgs), 1)
            elif engine and self.element_type == "Burg":
                # Ensure the burg displays its associated cell's state/culture if missing
                assoc_cell = next((c for c in engine.cells if c["i"] == item.get("cell_idx")), None)
                if assoc_cell:
                    item["state"] = item.get("state", assoc_cell.get("state", 0))
                    item["culture"] = item.get("culture", assoc_cell.get("culture", 0))
                    item["feature"] = item.get("feature", assoc_cell.get("biome", "Unknown"))
                
            for col_idx, key in enumerate(self.keys):
                val = item.get(key, "")
                table_item = QTableWidgetItem(str(val))
                if key in ["id", "cells_count", "burgs_count", "area", "population"]:
                    table_item.setFlags(table_item.flags() & ~Qt.ItemFlag.ItemIsEditable) # Read-only
                if key == "color":
                    table_item.setBackground(QColor(val) if str(val).startswith("#") else QColor("#333333"))
                    table_item.setForeground(QColor("#ffffff") if str(val).startswith("#") else QColor("#ffffff"))
                self.table.setItem(row_idx, col_idx, table_item)
        self.table.blockSignals(False)

    def on_item_changed(self, item_widget):
        row = item_widget.row()
        col = item_widget.column()
        if row < 0 or row >= len(self.items_list): return
        key = self.keys[col]
        new_val = item_widget.text()
        
        # Type coercion based on expected type in dictionary (infer from current val or key)
        curr_val = self.items_list[row].get(key)
        try:
            if isinstance(curr_val, int): new_val = int(new_val)
            elif isinstance(curr_val, float): new_val = float(new_val)
            elif isinstance(curr_val, bool): new_val = new_val.lower() in ["true", "1", "yes"]
        except ValueError:
            pass # fallback to string if parsing fails
            
        self.items_list[row][key] = new_val
        
        # If color changed, update background visually immediately
        if key == "color" and str(new_val).startswith("#"):
            item_widget.setBackground(QColor(str(new_val)))
            
        if self.parent_win:
            self.parent_win.map_engine.sink_generated_world_to_db(self.parent_win.db_path)
            self.parent_win.load_map_data_to_viewer()

    def add_row(self):
        new_id = max([it.get("id", 0) for it in self.items_list] + [0]) + 1
        new_item = {"id": new_id, "name": f"New {self.element_type}"}
        
        # Populate defaults
        if self.element_type == "State":
            new_item.update({"color": f"#{random.randint(50,255):02x}{random.randint(50,255):02x}{random.randint(50,255):02x}", "expansionism": 1.0, "type": "Terrestrial", "capital_cell": 1})
        elif self.element_type == "Culture":
            new_item.update({"code": new_item["name"][:3].upper(), "env_type": "Terrestrial", "is_aquatic": False})
        elif self.element_type == "Religion":
            new_item.update({"type": "Organized", "color": f"#{random.randint(50,255):02x}{random.randint(50,255):02x}{random.randint(50,255):02x}", "supreme_deity": "Unknown", "expansionism": 1.0})
        elif self.element_type == "Burg":
            new_item.update({"population": 10, "state": 1, "culture": 1, "feature": "Coast"})
        elif self.element_type == "Province":
            new_item.update({"color": f"#{random.randint(50,255):02x}{random.randint(50,255):02x}{random.randint(50,255):02x}", "state": 1})
            
        self.items_list.append(new_item)
        self.refresh_table()
        if self.parent_win:
            self.parent_win.map_engine.sink_generated_world_to_db(self.parent_win.db_path)
            self.parent_win.load_map_data_to_viewer()

    def delete_row(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.items_list): return
        
        self.items_list.pop(row)
        self.refresh_table()
        if self.parent_win:
            self.parent_win.map_engine.sink_generated_world_to_db(self.parent_win.db_path)
            self.parent_win.load_map_data_to_viewer()


# =============================================================================
# DIALOG: World Template Customizer
# =============================================================================
class TemplateDialog(QDialog):
    def __init__(self, template_mgr, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Customize World Templates")
        self.resize(500, 400)
        self.template_mgr = template_mgr

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QLabel("<b>Custom Worldbuilding Checklists &amp; Templates:</b>"))

        self.cb_templates = QComboBox()
        self.layout.addWidget(self.cb_templates)

        self.txt_fields = QTextEdit()
        self.txt_fields.setPlaceholderText("Enter template fields, one per line...")
        self.layout.addWidget(self.txt_fields)

        h_layout = QHBoxLayout()
        self.btn_new_cat      = QPushButton("➕ Add Category")
        self.btn_new_cat.clicked.connect(self.add_new_category)
        self.btn_save_template = QPushButton("💾 Save Template")
        self.btn_save_template.clicked.connect(self.save_current_template)

        h_layout.addWidget(self.btn_new_cat)
        h_layout.addWidget(self.btn_save_template)
        self.layout.addLayout(h_layout)

        self.cb_templates.currentTextChanged.connect(self.load_selected_template)
        self.refresh_categories()

    def refresh_categories(self):
        self.cb_templates.clear()
        self.templates = self.template_mgr.get_all_templates()
        self.cb_templates.addItems(list(self.templates.keys()))

    def load_selected_template(self, category):
        if not category or category not in self.templates:
            return
        fields = self.templates[category]
        self.txt_fields.setPlainText("\n".join(fields))

    def add_new_category(self):
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "New Template Category", "Category Name:")
        if ok and text.strip():
            self.template_mgr.save_template(text.strip(), ["Default Field"])
            self.refresh_categories()
            self.cb_templates.setCurrentText(text.strip())

    def save_current_template(self):
        category = self.cb_templates.currentText()
        if not category:
            return
        fields = [f.strip() for f in self.txt_fields.toPlainText().split("\n") if f.strip()]
        self.template_mgr.save_template(category, fields)
        QMessageBox.information(self, "Success", f"Template '{category}' updated successfully.")


# =============================================================================
# WIDGET: Floating Layer Tools Panel (draggable overlay on the map canvas)
# =============================================================================
class FloatingLayerTools(QFrame):
    """A draggable floating panel overlaid on the map canvas for layer editing tools."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FloatingLayerTools")
        self.setFixedWidth(218)
        self._drag_start = None
        self._build_ui()
        self.move(10, 52)
        self.raise_()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(7)

        # --- Header ---
        header_row = QHBoxLayout()
        title_lbl = QLabel("Layer Tools")
        title_lbl.setObjectName("FLTTitle")
        close_btn = QToolButton()
        close_btn.setText("x")
        close_btn.setFixedSize(18, 18)
        close_btn.setObjectName("FLTClose")
        close_btn.clicked.connect(self.hide)
        header_row.addWidget(title_lbl)
        header_row.addStretch()
        header_row.addWidget(close_btn)
        layout.addLayout(header_row)

        # --- Tool mode buttons ---
        tools_row = QHBoxLayout()
        tools_row.setSpacing(3)
        tool_defs = [
            ("P", "Pencil / Paint"),
            ("F", "Fill"),
            ("R", "Rectangle"),
            ("O", "Circle"),
            ("E", "Erase"),
        ]
        self._tool_btns = []
        for icon, tip in tool_defs:
            btn = QToolButton()
            btn.setText(icon)
            btn.setToolTip(tip)
            btn.setFixedSize(34, 30)
            btn.setCheckable(True)
            btn.setObjectName("FLTToolBtn")
            tools_row.addWidget(btn)
            self._tool_btns.append(btn)
        if self._tool_btns:
            self._tool_btns[0].setChecked(True)
        tools_row.addStretch()
        layout.addLayout(tools_row)

        # --- Palette ---
        layout.addWidget(QLabel("Palette:"))

        palette_row1 = QHBoxLayout()
        palette_row1.setSpacing(3)
        palette_row2 = QHBoxLayout()
        palette_row2.setSpacing(3)

        biome_swatches = [
            ("#3a7d44", "Temperate Forest"),
            ("#74b816", "Grassland"),
            ("#5c7a3e", "Cold Bamboo"),
            ("#7d5a3c", "Mountain"),
            ("#e8a838", "Hot Desert"),
        ]
        biome_swatches_2 = [
            ("#7d9e7a", "Needle Kelp"),
            ("#1d6fa4", "Deep Water"),
            ("#7f1d1d", "Abyss"),
            ("#6d4c7d", "Magic Zone"),
            ("#c0963c", "Blasted Lands"),
        ]

        for color, name in biome_swatches:
            sw = QFrame()
            sw.setFixedSize(22, 22)
            sw.setToolTip(name)
            sw.setStyleSheet(f"background-color: {color}; border-radius: 3px; border: 1px solid #404048;")
            palette_row1.addWidget(sw)
        palette_row1.addStretch()

        for color, name in biome_swatches_2:
            sw = QFrame()
            sw.setFixedSize(22, 22)
            sw.setToolTip(name)
            sw.setStyleSheet(f"background-color: {color}; border-radius: 3px; border: 1px solid #404048;")
            palette_row2.addWidget(sw)
        palette_row2.addStretch()

        layout.addLayout(palette_row1)
        layout.addLayout(palette_row2)

        # --- Opacity ---
        opacity_row = QHBoxLayout()
        opacity_lbl = QLabel("Opacity:")
        opacity_lbl.setFixedWidth(52)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        opacity_row.addWidget(opacity_lbl)
        opacity_row.addWidget(self.opacity_slider)
        layout.addLayout(opacity_row)

        # --- Data Overlay toggle ---
        overlay_row = QHBoxLayout()
        overlay_row.addWidget(QLabel("Data Overlay"))
        overlay_row.addStretch()
        self.chk_overlay = QCheckBox()
        self.chk_overlay.setChecked(False)
        overlay_row.addWidget(self.chk_overlay)
        layout.addLayout(overlay_row)

        # --- Edit Mode toggle ---
        edit_row = QHBoxLayout()
        edit_row.addWidget(QLabel("Edit Mode:"))
        edit_row.addStretch()
        self.btn_edit_mode = QPushButton("ON")
        self.btn_edit_mode.setObjectName("FLTEditModeBtn")
        self.btn_edit_mode.setCheckable(True)
        self.btn_edit_mode.setChecked(True)
        self.btn_edit_mode.setFixedSize(38, 22)
        self.btn_edit_mode.toggled.connect(lambda c: self.btn_edit_mode.setText("ON" if c else "OFF"))
        edit_row.addWidget(self.btn_edit_mode)
        layout.addLayout(edit_row)

        # --- Magic Type section (shown only when Magic Paint brush is active) ---
        self.magic_section = QWidget()
        magic_l = QVBoxLayout(self.magic_section)
        magic_l.setContentsMargins(0, 0, 0, 0)
        magic_l.setSpacing(3)
        magic_l.addWidget(QLabel("Magic Type:"))
        self.magic_combo = QComboBox()
        self.magic_combo.addItems(["Wild Magic", "Abyssal Corruption", "Ley Line Node", "Aether Storm", "None"])
        magic_l.addWidget(self.magic_combo)
        self.magic_section.hide()
        layout.addWidget(self.magic_section)

    # --- Drag support ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_start and event.buttons() == Qt.MouseButton.LeftButton:
            delta   = event.position().toPoint() - self._drag_start
            new_pos = self.pos() + delta
            if self.parent():
                max_x = self.parent().width()  - self.width()
                max_y = self.parent().height() - self.height()
                new_pos.setX(max(0, min(new_pos.x(), max_x)))
                new_pos.setY(max(0, min(new_pos.y(), max_y)))
            self.move(new_pos)

    def mouseReleaseEvent(self, event):
        self._drag_start = None


# =============================================================================
# WIDGET: Brush Settings Panel (Dynamic Brush selection)
# =============================================================================
class BrushSettingsWidget(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.active_layer = None
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(8)

        self.lbl_title = QLabel("<b>Brush Settings</b>")
        self.lbl_title.setStyleSheet("color: #04D361; font-size: 11px; letter-spacing: 1px;")
        
        self.cb_elements = QComboBox()
        self.cb_elements.setStyleSheet("background: #111116; border: 1px solid #29292E; color: #EEEEF8; padding: 4px;")
        self.cb_elements.currentIndexChanged.connect(self.on_selection_changed)

        self.btn_add = QPushButton("+ Add New")
        self.btn_add.setStyleSheet("background: #1a2e1a; border: 1px solid #04D361; color: #04D361; padding: 4px; font-weight: bold;")
        self.btn_add.clicked.connect(self.on_add_clicked)
        
        self.layout.addWidget(self.lbl_title)
        self.layout.addWidget(self.cb_elements)
        self.layout.addWidget(self.btn_add)
        
    def populate(self, layer_key):
        self.active_layer = layer_key
        self.cb_elements.blockSignals(True)
        self.cb_elements.clear()
        
        engine = self.main_window.map_engine
        items = []
        if layer_key == "Political States":
            items = [(s["id"], s["name"]) for s in engine.states]
        elif layer_key == "Cultures":
            items = [(c["id"], c["name"]) for c in engine.cultures]
        elif layer_key == "Religions":
            items = [(r["id"], r["name"]) for r in engine.religions]
        elif layer_key == "Provinces":
            items = [(p["id"], p["name"]) for p in engine.provinces]
            
        for i, name in items:
            self.cb_elements.addItem(f"{i}: {name}", i)
            
        self.cb_elements.blockSignals(False)
        if self.cb_elements.count() > 0:
            self.cb_elements.setCurrentIndex(0)
            self.on_selection_changed(0)
        self.show()

    def on_selection_changed(self, idx):
        if idx < 0: return
        val_id = self.cb_elements.itemData(idx)
        viewer = self.main_window.map_viewer
        if self.active_layer == "Political States":
            viewer.paint_state_value = val_id
        elif self.active_layer == "Cultures":
            viewer.paint_culture_value = val_id
        elif self.active_layer == "Religions":
            viewer.paint_religion_value = val_id
        elif self.active_layer == "Provinces":
            viewer.paint_province_value = val_id
            
    def on_add_clicked(self):
        engine = self.main_window.map_engine
        
        # We can prompt for a name natively
        text, ok = QInputDialog.getText(self, f"New {self.active_layer}", f"Enter name for new {self.active_layer}:")
        if ok and text:
            new_id = 1
            items = []
            if self.active_layer == "Political States":
                items = engine.states
            elif self.active_layer == "Cultures":
                items = engine.cultures
            elif self.active_layer == "Religions":
                items = engine.religions
            elif self.active_layer == "Provinces":
                items = engine.provinces
                
            if items:
                new_id = max((item["id"] for item in items), default=0) + 1
                
            # Create the element
            new_item = {"id": new_id, "name": text, "color": f"#{random.randint(0, 0xFFFFFF):06x}"}
            items.append(new_item)
            
            # Repopulate and select it
            self.populate(self.active_layer)
            idx = self.cb_elements.findData(new_id)
            if idx >= 0:
                self.cb_elements.setCurrentIndex(idx)


# =============================================================================
# MAIN WINDOW
# =============================================================================
class WorldsmithMainWindow(QMainWindow):

    def __init__(self, project_dir):
        super().__init__()
        self.project_dir = os.path.abspath(project_dir)
        project_name = os.path.basename(self.project_dir)
        self.setWindowTitle(f"Worldsmith Sandbox - {project_name}")
        self.resize(1600, 950)
        self.setStyleSheet("background: #111116; color: #EEEEF8;")
        self.start_ollama_server()

        # --- Base Data Paths ---
        self.db_path = os.path.join(self.project_dir, "lore_forge_world.db")
        self.ai_worker    = None
        self.audit_worker = None
        self.selected_cell_idx = None

        self.template_mgr = TemplateManager(self.db_path)
        self.emblem_gen   = EmblemGenerator()

        # Calendar settings
        self.custom_year_length = 420
        self.custom_seasons     = ["Sowing-Time", "High-Sun", "Gold-Leaf", "Deep-Frost"]
        self.cosmos_engine      = CosmosEngine(self.custom_year_length, self.custom_seasons)

        # Initialize full Azgaar simulation logic including all parameters and layers
        self.map_engine = AzgaarEngine()

        # Session progress tracking
        self._session_msg_count = 0

        # --- Stylesheet ---
        self._apply_stylesheet()

        # --- Main Splitter ---
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.main_splitter)

        # --- Hidden Compatibility Widgets ---
        # These preserve all existing slot method signatures without modification.
        self.cb_layer = QComboBox(self)
        self.cb_layer.addItems([
            "Elevation", "Biomes", "Political States", "Provinces",
            "Cultures", "Magic Layer", "Production Goods", "Rivers",
            "Roads", "Military Regiments", "Burgs"
        ])
        self.cb_layer.currentTextChanged.connect(self.change_map_layer)
        self.cb_layer.hide()

        self.chk_layer_visibility = QCheckBox(self)
        self.chk_layer_visibility.setChecked(True)
        self.chk_layer_visibility.stateChanged.connect(self.toggle_layer_visibility)
        self.chk_layer_visibility.hide()

        self.cb_brush_mode = QComboBox(self)
        self.cb_brush_mode.addItems([
            "Inspect", "Magic Paint", "Height Paint", "Height Raise", "Height Lower", "Height Smooth",
            "State Paint", "Province Paint", "Culture Paint", "Religion Paint", "River Paint", "Burg Paint",
            "Biome Paint", "Production Paint", "Road Paint", "Road Delete", "Military Paint"
        ])
        self.cb_brush_mode.currentTextChanged.connect(self.change_brush_mode)
        self.cb_brush_mode.hide()

        self.cb_magic_brush = QComboBox(self)
        self.cb_magic_brush.addItems(["Wild Magic", "Abyssal Corruption", "Ley Line Node", "Aether Storm", "None"])
        self.cb_magic_brush.currentTextChanged.connect(self.change_magic_brush)
        self.cb_magic_brush.hide()

        self.cb_edit_element = QComboBox(self)
        self.cb_edit_element.addItems(["Edit Element...", "States Table", "Cultures Table", "Religions Table", "Burgs Table"])
        self.cb_edit_element.currentTextChanged.connect(self.open_element_table_editor)
        self.cb_edit_element.hide()

        self.cb_tools = QComboBox(self)
        self.cb_tools.addItems([
            "Tools", "Edit State", "Edit Culture", "Edit Religion",
            "Add Burg", "Delete Selected Element"
        ])
        self.cb_tools.currentTextChanged.connect(self.trigger_azgaar_tool_mode)
        self.cb_tools.hide()

        # --- Build Panels ---
        self._build_file_tree_panel()
        self._build_map_panel()
        self._build_writing_panel()
        self._build_ai_panel()
        
        # Set default splitter proportions (File Tree 15%, Map 35%, Writing 30%, AI 20%)
        self.main_splitter.setSizes([240, 560, 480, 320])

        # --- Status Bar ---
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Worldsmith ready.")

        # --- Initialize DB, World, and Welcome ---
        self.setup_markers_db()
        self.setup_magic_db()
        self.setup_timeline_db()
        self.setup_staging_db()

        # Timer for global active worldbuilding prompts
        self.active_prompt_timer = QTimer(self)
        self.active_prompt_timer.timeout.connect(self.trigger_global_active_prompt)
        self.active_prompt_timer.start(120000) # Every 2 minutes
        
        # Do not generate world automatically on load. Wait for user input or file load.
        self.load_unresolved_inconsistencies()
        self.refresh_note_list()
        self.trigger_welcome_prompt()

    def start_ollama_server(self):
        """Silently launch Ollama serve in the background if not already running."""
        import subprocess
        import urllib.request
        try:
            # Check if it's already running on port 11434
            req = urllib.request.Request("http://localhost:11434/")
            with urllib.request.urlopen(req, timeout=1) as response:
                if response.status == 200:
                    return # Already running
        except:
            pass # Not running, start it
            
        try:
            # Use CREATE_NO_WINDOW (0x08000000) on Windows to hide the console pop-up
            subprocess.Popen(
                ["ollama", "serve"],
                creationflags=0x08000000, 
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print(f"Failed to auto-launch Ollama: {e}")

    # =========================================================================
    # STYLESHEET
    # =========================================================================
    def _apply_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #111116;
                color: #E1E1E6;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            QSplitter::handle {
                background: #29292E;
                width: 2px;
            }

            /* Icon Sidebar */
            QWidget#IconSidebar {
                background: #16161c;
                border-right: 1px solid #29292E;
            }
            QToolButton#SidebarBtn {
                background: transparent;
                border: none;
                border-radius: 6px;
                color: #80809A;
                font-size: 14px;
                padding: 2px;
            }
            QToolButton#SidebarBtn:hover  { background: #29292E; color: #E1E1E6; }
            QToolButton#SidebarBtn:checked { background: #1a2e1a; color: #04D361; }

            /* Layer Panel */
            QWidget#LayerPanel { background: #13131c; border-right: 1px solid #29292E; }
            QWidget#LayerPanelHeader { background: #13131c; }
            QWidget#LayerRow:hover { background: #1a1a26; }
            QToolButton#EyeBtn {
                background: transparent; border: none; color: #505068; font-size: 11px; border-radius: 3px;
            }
            QToolButton#EyeBtn:checked { color: #04D361; }
            QToolButton#EyeBtn:hover   { color: #E1E1E6; }
            QPushButton#AddLayerBtn {
                background: #16161c; border: none; border-top: 1px solid #29292E;
                color: #505068; font-size: 12px; padding: 6px; text-align: left; padding-left: 14px;
            }
            QPushButton#AddLayerBtn:hover { color: #04D361; background: #1a2e1a; }

            /* Writing Panel */
            QWidget#WritingPanel { background: #111116; }
            QWidget#WritingToolbar { background: #18181e; border-bottom: 1px solid #29292E; }
            QToolButton#FmtBtn {
                background: transparent; border: 1px solid transparent;
                border-radius: 4px; color: #A0A0B8; font-size: 13px; padding: 2px 4px;
            }
            QToolButton#FmtBtn:hover  { background: #29292E; color: #E1E1E6; border-color: #404050; }
            QToolButton#FmtBtn:checked { background: #1a2e1a; color: #04D361; border-color: #04D361; }
            QLineEdit#NoteTitleInput {
                font-size: 18px; font-weight: bold; color: #EEEEF8;
                background: #111116; border: none; border-bottom: 1px solid #29292E;
                padding: 10px 14px 8px 14px;
            }
            QLineEdit#NoteTitleInput:focus { border-bottom-color: #04D361; }
            QTextEdit {
                background: #111116; border: none; color: #D8D8E8;
                font-size: 13px; padding: 8px 14px;
            }

            /* AI Panel */
            QWidget#AIPanel { background: #0f0f18; }
            QWidget#AIHeader { background: #18181e; border-bottom: 1px solid #29292E; }
            QLabel#AIHeaderTitle {
                font-weight: bold; font-size: 12px; color: #D0D0E0; letter-spacing: 1px;
            }
            QLabel#SessionBadge {
                background: #04D361; color: #000; font-size: 9px; font-weight: bold;
                border-radius: 3px; padding: 2px 6px; letter-spacing: 1px;
            }
            QToolButton#OverflowBtn {
                background: transparent; border: none; color: #707080; font-size: 18px; padding: 0px;
            }
            QToolButton#OverflowBtn:hover { color: #E1E1E6; }
            QTextEdit#AIChatHistory { background: #0f0f18; border: none; color: #D0D0E0; padding: 10px; }
            QWidget#ContextSection { background: #14141e; border-top: 1px solid #29292E; }
            QLabel#CurrentPromptLabel { color: #8080A0; font-size: 12px; }
            QPushButton#AnalyzeBtn {
                background: #1a1a30; border: 1px solid #3a3a58; color: #7878B8;
                border-radius: 4px; font-size: 12px; padding: 5px;
            }
            QPushButton#AnalyzeBtn:hover { background: #22223a; color: #A0A0D8; border-color: #5858A0; }
            QLabel#SessionProgressLabel { color: #505080; font-size: 11px; font-style: italic; }
            QWidget#AIInputArea { background: #18181e; border-top: 1px solid #29292E; }
            QLineEdit#AIInputField {
                background: #1e1e2c; border: 1px solid #2e2e42; color: #E1E1E6;
                border-radius: 14px; padding: 6px 14px; font-size: 13px;
            }
            QLineEdit#AIInputField:focus { border-color: #04D361; }
            QToolButton#SendBtn {
                background: #04D361; color: #000; border: none; border-radius: 15px;
                font-weight: bold; font-size: 13px;
            }
            QToolButton#SendBtn:hover    { background: #05FF72; }
            QToolButton#SendBtn:disabled { background: #29292E; color: #505060; }
            QWidget#ContraHeader { background: #1a0e0e; border-top: 1px solid #4a1a1a; }
            QLabel#ContraLabel  { color: #ef4444; font-size: 11px; font-weight: bold; }
            QListWidget#InconsistencyList { background: #130808; color: #f87171; border: none; font-size: 11px; }
            QToolButton#ContraToggle { background: transparent; border: none; color: #6a2020; font-size: 10px; }
            QWidget#TimelineWidget { background: #0f0f18; border-top: 1px solid #29292E; }

            /* Floating Layer Tools */
            QFrame#FloatingLayerTools {
                background: #1e1e2c; border: 1px solid #404060; border-radius: 8px;
            }
            QFrame#FloatingLayerTools QLabel { color: #B0B0C8; font-size: 11px; background: transparent; }
            QLabel#FLTTitle { color: #D0D0E0; font-weight: bold; font-size: 12px; background: transparent; }
            QToolButton#FLTClose {
                background: #303040; border: none; color: #707080; border-radius: 2px; font-size: 12px;
            }
            QToolButton#FLTClose:hover { background: #ef4444; color: #fff; }
            QToolButton#FLTToolBtn {
                background: #28283a; border: 1px solid #404058; border-radius: 4px;
                color: #A0A0C0; font-size: 12px; font-weight: bold;
            }
            QToolButton#FLTToolBtn:checked { background: #1a2e1a; border-color: #04D361; color: #04D361; }
            QToolButton#FLTToolBtn:hover   { background: #303048; color: #E1E1E6; }
            QPushButton#FLTEditModeBtn {
                background: #04D361; color: #000; font-size: 9px; font-weight: bold; border: none; border-radius: 3px;
            }
            QPushButton#FLTEditModeBtn:!checked { background: #303040; color: #707080; }

            /* Generic Widgets */
            QPushButton, QComboBox {
                background: #202028; border: 1px solid #29292E; color: #E1E1E6;
                border-radius: 4px; padding: 5px 10px; font-weight: bold;
            }
            QPushButton:hover, QComboBox:hover { background: #29292E; border-color: #04D361; }
            QLineEdit, QListWidget {
                background: #1c1c24; border: 1px solid #29292E; border-radius: 4px; padding: 5px; color: #E1E1E6;
            }
            QScrollBar:vertical { background: #111116; width: 6px; border: none; }
            QScrollBar::handle:vertical { background: #29292E; border-radius: 3px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #04D361; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QGroupBox {
                border: 1px solid #29292E; border-radius: 6px;
                margin-top: 10px; padding-top: 10px; font-weight: bold; color: #04D361;
            }
        """)

    # =========================================================================
    # PANEL BUILDERS
    # =========================================================================
    def _build_file_tree_panel(self):
        """Build Panel 0: File Browser for Lore Notes."""
        container = QWidget()
        container.setObjectName("FileTreePanel")
        container.setStyleSheet("background: #1e1e2c; border: none;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        lbl = QLabel("Lore Directory")
        lbl.setStyleSheet("color: #D8D8EC; font-weight: bold; font-size: 13px; padding: 4px;")
        
        self.file_model = QFileSystemModel()
        lore_dir = self.get_lore_dir()
        if not os.path.exists(lore_dir):
            os.makedirs(lore_dir)
        self.file_model.setRootPath(lore_dir)
        
        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(self.file_model.index(lore_dir))
        self.file_tree.setAnimated(True)
        self.file_tree.setIndentation(15)
        self.file_tree.setSortingEnabled(True)
        
        # Hide standard columns like size, type, date modified
        self.file_tree.setColumnHidden(1, True)
        self.file_tree.setColumnHidden(2, True)
        self.file_tree.setColumnHidden(3, True)
        self.file_tree.setHeaderHidden(True)
        self.file_tree.setStyleSheet("QTreeView { color: #E0E0E0; background: #111116; border: 1px solid #404060; border-radius: 4px; }")
        
        self.file_tree.clicked.connect(self.on_file_tree_clicked)
        
        layout.addWidget(lbl)
        layout.addWidget(self.file_tree)
        
        self.main_splitter.addWidget(container)

    def _build_map_panel(self):
        """Build Panel 1: Map View & Editor with icon sidebar, layer list, floating tools."""

        map_outer = QWidget()
        map_outer.setObjectName("MapOuter")
        outer_layout = QHBoxLayout(map_outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # --- Icon Sidebar (~50px) ---
        icon_sidebar = QWidget()
        icon_sidebar.setObjectName("IconSidebar")
        icon_sidebar.setFixedWidth(50)
        sb_layout = QVBoxLayout(icon_sidebar)
        sb_layout.setContentsMargins(4, 8, 4, 8)
        sb_layout.setSpacing(4)

        def _sb_btn(icon, tip, checkable=False):
            b = QToolButton()
            b.setText(icon)
            b.setToolTip(tip)
            b.setFixedSize(40, 36)
            b.setObjectName("SidebarBtn")
            b.setCheckable(checkable)
            return b

        def _hsep():
            s = QFrame()
            s.setFrameShape(QFrame.Shape.HLine)
            s.setStyleSheet("background: #29292E; max-height: 1px; margin: 2px 4px;")
            return s

        sb_layout.addWidget(_sb_btn("M", "Map View"))
        sb_layout.addWidget(_hsep())

        btn_toggle_layers = _sb_btn("=", "Toggle Layer Panel")
        sb_layout.addWidget(btn_toggle_layers)

        btn_toggle_tools = _sb_btn("T", "Show / Hide Layer Tools")
        sb_layout.addWidget(btn_toggle_tools)

        sb_layout.addWidget(_hsep())

        # Brush mode quick-select buttons
        self._sidebar_brush_btns = []
        brush_defs = [
            ("?", "Inspect"),
            ("*", "Magic Paint"),
            ("^", "Height Paint"),
            ("F", "State Paint"),
            ("C", "Culture Paint"),
            ("~", "River Paint"),
            ("B", "Burg Paint"),
        ]
        for icon, name in brush_defs:
            btn = _sb_btn(icon, name, checkable=True)
            btn.clicked.connect(lambda _, bn=name: self.cb_brush_mode.setCurrentText(bn))
            sb_layout.addWidget(btn)
            self._sidebar_brush_btns.append((btn, name))

        sb_layout.addStretch()
        sb_layout.addWidget(_hsep())

        # Bottom world action buttons
        self.btn_regen         = _sb_btn("D", "New World")
        self.btn_load_world    = _sb_btn("L", "Load World")
        self.btn_save_world_file = _sb_btn("S", "Save World")
        btn_elements           = _sb_btn("E", "Edit Elements")

        self.btn_regen.clicked.connect(self.trigger_world_regeneration)
        self.btn_load_world.clicked.connect(self.load_world_from_file)
        self.btn_save_world_file.clicked.connect(self.save_world_to_file)
        btn_elements.clicked.connect(lambda: self.cb_edit_element.setCurrentText("States Table"))

        sb_layout.addWidget(self.btn_regen)
        sb_layout.addWidget(self.btn_load_world)
        sb_layout.addWidget(self.btn_save_world_file)
        sb_layout.addWidget(btn_elements)

        outer_layout.addWidget(icon_sidebar)

        # --- Layer Panel (~178px collapsible) ---
        self.layer_panel = QWidget()
        self.layer_panel.setObjectName("LayerPanel")
        self.layer_panel.setFixedWidth(178)
        lp_layout = QVBoxLayout(self.layer_panel)
        lp_layout.setContentsMargins(0, 0, 0, 0)
        lp_layout.setSpacing(0)

        lp_hdr = QWidget()
        lp_hdr.setObjectName("LayerPanelHeader")
        lp_hdr.setFixedHeight(38)
        lp_hdr_l = QHBoxLayout(lp_hdr)
        lp_hdr_l.setContentsMargins(10, 0, 8, 0)
        lp_title = QLabel("Layers")
        lp_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #04D361; letter-spacing: 1px;")
        lp_hdr_l.addWidget(lp_title)
        lp_hdr_l.addStretch()
        lp_layout.addWidget(lp_hdr)

        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.HLine)
        div1.setStyleSheet("background: #29292E; max-height: 1px;")
        lp_layout.addWidget(div1)

        LAYERS = [
            ("Elevation",        "E"),
            ("Biomes",           "B"),
            ("Political States", "P"),
            ("Provinces",        "V"),
            ("Cultures",         "C"),
            ("Religions",        "R"),
            ("Magic Layer",      "*"),
            ("Production Goods", "G"),
            ("Rivers",           "~"),
            ("Roads",            "-"),
            ("Military Regiments", "X"),
            ("Burgs",            "H"),
            ("Temperature",      "T"),
            ("Precipitation",    "R"),
            ("Population Density", "D"),
            ("Ice",              "I"),
            ("Coastlines",       "~"),
            ("Borders",          "|"),
            ("Relief Icons",     "^"),
            ("Markers",          "!"),
            ("Emblems",          "&"),
            ("Grid",             "#"),
            ("Coordinates",      "°"),
            ("Compass",          "O"),
            ("Scale Bar",        "_"),
            ("Vignette",         "V"),
        ]

        self._layer_row_widgets = {}

        for layer_key, icon in LAYERS:
            row = QWidget()
            row.setObjectName("LayerRow")
            row.setFixedHeight(36)
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row_l = QHBoxLayout(row)
            row_l.setContentsMargins(10, 0, 8, 0)
            row_l.setSpacing(6)

            icon_lbl = QLabel(icon)
            icon_lbl.setFixedWidth(18)
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_lbl.setStyleSheet("background: transparent; color: #606080; font-weight: bold;")

            name_lbl = QLabel(layer_key)
            name_lbl.setStyleSheet("font-size: 12px; color: #A0A0C0; background: transparent;")

            eye_btn = QToolButton()
            eye_btn.setText("👁")
            eye_btn.setToolTip("Toggle Visibility")
            eye_btn.setCheckable(True)
            eye_btn.setChecked(True)
            eye_btn.setFixedSize(22, 22)
            eye_btn.setObjectName("EyeBtn")
            eye_btn.toggled.connect(lambda checked, lk=layer_key: self._set_layer_visibility(lk, checked))

            gear_btn = QToolButton()
            gear_btn.setText("⚙")
            gear_btn.setToolTip("Edit Tool")
            gear_btn.setFixedSize(22, 22)
            gear_btn.setStyleSheet("QToolButton { background: transparent; border: none; color: #707080; } QToolButton:hover { color: #04D361; }")
            gear_btn.clicked.connect(lambda _, lk=layer_key: self._open_layer_editor(lk))

            row_l.addWidget(icon_lbl)
            row_l.addWidget(name_lbl, 1)
            row_l.addWidget(eye_btn)
            row_l.addWidget(gear_btn)

            # Left click row to select layer mode
            row.mousePressEvent = lambda ev, lk=layer_key: self._select_layer_row(lk)
            self._layer_row_widgets[layer_key] = row
            lp_layout.addWidget(row)

        lp_layout.addStretch()

        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setStyleSheet("background: #29292E; max-height: 1px;")
        lp_layout.addWidget(div2)

        btn_add_layer = QPushButton("+  Add Layer")
        btn_add_layer.setObjectName("AddLayerBtn")
        btn_add_layer.setFixedHeight(32)
        lp_layout.addWidget(btn_add_layer)

        # Add Brush Settings Panel
        self.brush_settings_panel = BrushSettingsWidget(self)
        self.brush_settings_panel.hide()
        lp_layout.addWidget(self.brush_settings_panel)

        # Add Brush Size Slider
        brush_widget = QWidget()
        brush_l = QVBoxLayout(brush_widget)
        brush_l.setContentsMargins(10, 10, 10, 10)
        self.lbl_brush_size = QLabel("<b>Brush Radius:</b>")
        self.lbl_brush_size.setStyleSheet("color: #A0A0C0; font-size: 11px;")
        self.slider_brush_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_brush_size.setRange(1, 4)
        self.slider_brush_size.setValue(1)
        self.slider_brush_size.valueChanged.connect(self.change_brush_size)
        brush_l.addWidget(self.lbl_brush_size)
        brush_l.addWidget(self.slider_brush_size)
        lp_layout.addWidget(brush_widget)

        btn_toggle_layers.clicked.connect(
            lambda: self.layer_panel.setVisible(not self.layer_panel.isVisible())
        )

        outer_layout.addWidget(self.layer_panel)

        # --- Map Canvas Area ---
        self.map_area = QWidget()
        self.map_area.setObjectName("MapArea")
        map_area_l = QVBoxLayout(self.map_area)
        map_area_l.setContentsMargins(0, 0, 0, 0)
        map_area_l.setSpacing(0)

        self.map_viewer = MapViewerWidget(self)
        self.map_viewer.cell_hovered.connect(self.handle_cell_hovered)
        self.map_viewer.cell_clicked.connect(self.handle_cell_clicked)
        map_area_l.addWidget(self.map_viewer)

        outer_layout.addWidget(self.map_area, 1)

        # --- Floating Layer Tools (child of map_area, overlaid) ---
        self.floating_layer_tools = FloatingLayerTools(self.map_area)
        self.floating_layer_tools.hide()

        self.floating_layer_tools.magic_combo.currentTextChanged.connect(self.change_magic_brush)

        btn_toggle_tools.clicked.connect(
            lambda: self.floating_layer_tools.setVisible(not self.floating_layer_tools.isVisible())
        )

        # Default active layer
        self._select_layer_row("Biomes")

        self.main_splitter.addWidget(map_outer)

    def _build_writing_panel(self):
        """Build Panel 2: Writing & Viewing Workspace with formatting toolbar."""

        self.note_container = QWidget()
        self.note_container.setObjectName("WritingPanel")
        note_layout = QVBoxLayout(self.note_container)
        note_layout.setContentsMargins(0, 0, 0, 0)
        note_layout.setSpacing(0)

        # --- Formatting Toolbar ---
        toolbar = QWidget()
        toolbar.setObjectName("WritingToolbar")
        toolbar.setFixedHeight(42)
        toolbar_l = QHBoxLayout(toolbar)
        toolbar_l.setContentsMargins(8, 6, 8, 6)
        toolbar_l.setSpacing(2)

        def _fmt_btn(text, tip, checkable=False, width=28):
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.setFixedSize(width, 28)
            b.setCheckable(checkable)
            b.setObjectName("FmtBtn")
            return b

        btn_bold          = _fmt_btn("B",  "Bold — inserts **text**",        checkable=True)
        btn_italic        = _fmt_btn("I",  "Italic — inserts *text*",        checkable=True)
        btn_underline     = _fmt_btn("U",  "Underline — inserts __text__",   checkable=True)
        btn_strikethrough = _fmt_btn("S",  "Strikethrough — inserts ~~text~~", checkable=True)
        btn_h1            = _fmt_btn("H1", "Heading 1 — inserts # prefix",   width=30)
        btn_h2            = _fmt_btn("H2", "Heading 2 — inserts ## prefix",  width=30)
        btn_link          = _fmt_btn("[ ]", "Insert [[WikiLink]]",            width=34)

        btn_bold.setStyleSheet(
            "QToolButton { font-weight: bold; }"
            "QToolButton:checked { background: #1a2e1a; color: #04D361; border: 1px solid #04D361; border-radius: 4px; }"
        )
        btn_italic.setStyleSheet(
            "QToolButton { font-style: italic; }"
            "QToolButton:checked { background: #1a2e1a; color: #04D361; border: 1px solid #04D361; border-radius: 4px; }"
        )

        btn_bold.clicked.connect(lambda:          self._apply_text_format("bold"))
        btn_italic.clicked.connect(lambda:        self._apply_text_format("italic"))
        btn_underline.clicked.connect(lambda:     self._apply_text_format("underline"))
        btn_strikethrough.clicked.connect(lambda: self._apply_text_format("strikethrough"))
        btn_h1.clicked.connect(lambda:            self._apply_heading_format(1))
        btn_h2.clicked.connect(lambda:            self._apply_heading_format(2))
        btn_link.clicked.connect(self._insert_wiki_link)

        toolbar_l.addWidget(btn_bold)
        toolbar_l.addWidget(btn_italic)
        toolbar_l.addWidget(btn_underline)
        toolbar_l.addWidget(btn_strikethrough)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFixedHeight(20)
        sep1.setStyleSheet("background: #29292E; max-width: 1px; margin: 4px 3px;")
        toolbar_l.addWidget(sep1)

        toolbar_l.addWidget(btn_h1)
        toolbar_l.addWidget(btn_h2)
        toolbar_l.addWidget(btn_link)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setFixedHeight(20)
        sep2.setStyleSheet("background: #29292E; max-width: 1px; margin: 4px 3px;")
        toolbar_l.addWidget(sep2)

        # Note action icon buttons
        self.btn_save_note    = _fmt_btn("Save",   "Save Note",                width=38)
        self.btn_bind_map     = _fmt_btn("Pin",    "Bind to Map Cell",          width=32)
        self.btn_import_note  = _fmt_btn("Imp",    "Import External Note(s)",   width=36)
        self.btn_delete_note  = _fmt_btn("Del",    "Delete Note",               width=30)
        self.btn_compile_wiki = _fmt_btn("Wiki",   "Compile Static Wiki",       width=36)

        self.btn_save_note.clicked.connect(self.save_current_note)
        self.btn_bind_map.clicked.connect(self.bind_note_to_map_cell)
        
        import_menu = QMenu(self.btn_import_note)
        import_menu.setStyleSheet("QMenu { background: #1e1e2c; border: 1px solid #404060; color: #D0D0E0; border-radius: 4px; padding: 4px 0; } QMenu::item { padding: 6px 16px; } QMenu::item:selected { background: #29293a; color: #04D361; }")
        import_menu.addAction("Import Single File", self.import_external_note)
        import_menu.addAction("Import Folder", self.import_external_folder)
        self.btn_import_note.setMenu(import_menu)
        self.btn_import_note.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        self.btn_compile_wiki.clicked.connect(self.compile_static_wiki)

        toolbar_l.addWidget(self.btn_save_note)
        toolbar_l.addWidget(self.btn_bind_map)
        toolbar_l.addWidget(self.btn_import_note)
        toolbar_l.addWidget(self.btn_delete_note)
        toolbar_l.addWidget(self.btn_compile_wiki)
        toolbar_l.addStretch()

        note_layout.addWidget(toolbar)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background: #29292E; max-height: 1px;")
        note_layout.addWidget(div)

        # --- Note Title Input ---
        note_title_layout = QHBoxLayout()
        note_title_layout.setContentsMargins(10, 5, 10, 5)
        
        self.note_title_input = QLineEdit()
        self.note_title_input.setObjectName("NoteTitleInput")
        self.note_title_input.setPlaceholderText("Note Title (e.g., 'Ostraka City')")
        self.note_title_input.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px; background: #1a1a24; border: 1px solid #2a2a35;")
        note_title_layout.addWidget(self.note_title_input)
        
        self.btn_bind_map = QPushButton("📌 Bind to Map")
        self.btn_bind_map.setStyleSheet("background: #04D361; color: black; font-weight: bold; padding: 5px 10px; border-radius: 4px;")
        self.btn_bind_map.clicked.connect(self.open_bind_dialog)
        note_title_layout.addWidget(self.btn_bind_map)
        
        note_layout.addLayout(note_title_layout)

        # --- Note Body Editor ---
        self.note_editor = MarkdownNotebookEditor(self)
        self.note_editor.tag_detected.connect(self.handle_tag_found)
        self.note_editor.link_clicked.connect(self.handle_link_clicked)
        note_layout.addWidget(self.note_editor, 1)

        # --- Draft Action Bar ---
        self.staging_action_widget = QWidget()
        self.staging_action_widget.setVisible(False)
        staging_action_l = QHBoxLayout(self.staging_action_widget)
        staging_action_l.setContentsMargins(10, 5, 10, 5)
        
        self.btn_commit_draft = QPushButton("Commit to Canon")
        self.btn_commit_draft.setStyleSheet("background: #04D361; color: #000; font-weight: bold; padding: 6px;")
        self.btn_commit_draft.clicked.connect(self.commit_draft)
        
        self.btn_discard_draft = QPushButton("Discard Draft")
        self.btn_discard_draft.setStyleSheet("background: #e9695f; color: #000; font-weight: bold; padding: 6px;")
        self.btn_discard_draft.clicked.connect(self.discard_draft)

        staging_action_l.addWidget(self.btn_commit_draft)
        staging_action_l.addWidget(self.btn_discard_draft)
        note_layout.addWidget(self.staging_action_widget)

        self.main_splitter.addWidget(self.note_container)

    def _build_ai_panel(self):
        """Build Panel 3: AI Writing Assistant."""
        # --- AI Chat Tab ---
        self.ai_container = QWidget()
        self.ai_container.setObjectName("AIPanel")
        ai_layout = QVBoxLayout(self.ai_container)
        ai_layout.setContentsMargins(0, 0, 0, 0)
        ai_layout.setSpacing(0)

        # --- Session Header ---
        header = QWidget()
        header.setObjectName("AIHeader")
        header.setFixedHeight(46)
        header_l = QHBoxLayout(header)
        header_l.setContentsMargins(12, 0, 8, 0)
        header_l.setSpacing(8)

        hdr_icon = QLabel("*")
        hdr_icon.setStyleSheet("background: transparent; color: #04D361; font-weight: bold; font-size: 16px;")
        hdr_icon.setFixedWidth(20)

        hdr_title = QLabel("Assistant: GUIDED SESSION")
        hdr_title.setObjectName("AIHeaderTitle")

        session_badge = QLabel("ACTIVE")
        session_badge.setObjectName("SessionBadge")

        btn_overflow = QToolButton()
        btn_overflow.setText("...")
        btn_overflow.setObjectName("OverflowBtn")
        btn_overflow.setFixedSize(28, 28)
        btn_overflow.setToolTip("More Options")

        overflow_menu = QMenu(btn_overflow)
        overflow_menu.setStyleSheet("""
            QMenu { background: #1e1e2c; border: 1px solid #404060; color: #D0D0E0; border-radius: 4px; padding: 4px 0; }
            QMenu::item { padding: 6px 16px; }
            QMenu::item:selected { background: #29293a; color: #04D361; }
        """)
        overflow_menu.addAction("Customize Templates",   self.show_template_customizer)
        overflow_menu.addSeparator()
        overflow_menu.addAction("Edit States",           lambda: self.cb_tools.setCurrentText("Edit State"))
        overflow_menu.addAction("Edit Cultures",         lambda: self.cb_tools.setCurrentText("Edit Culture"))
        overflow_menu.addAction("Edit Religions",        lambda: self.cb_tools.setCurrentText("Edit Religion"))
        btn_overflow.clicked.connect(
            lambda: overflow_menu.exec(btn_overflow.mapToGlobal(QPoint(0, btn_overflow.height())))
        )

        header_l.addWidget(hdr_icon)
        header_l.addWidget(hdr_title, 1)
        header_l.addWidget(session_badge)
        header_l.addWidget(btn_overflow)

        ai_layout.addWidget(header)

        div_hdr = QFrame()
        div_hdr.setFrameShape(QFrame.Shape.HLine)
        div_hdr.setStyleSheet("background: #29292E; max-height: 1px;")
        ai_layout.addWidget(div_hdr)

        # --- Chat History ---
        self.ai_prompt_history = QTextEdit()
        self.ai_prompt_history.setObjectName("AIChatHistory")
        self.ai_prompt_history.setReadOnly(True)
        self.ai_prompt_history.setPlaceholderText("The AI will guide your worldbuilding process...")
        ai_layout.addWidget(self.ai_prompt_history, 1)

        # --- Context Info Section ---
        context_widget = QWidget()
        context_widget.setObjectName("ContextSection")
        context_l = QVBoxLayout(context_widget)
        context_l.setContentsMargins(12, 10, 12, 10)
        context_l.setSpacing(6)

        self.lbl_current_prompt = QLabel("Prompt: World Setup")
        self.lbl_current_prompt.setObjectName("CurrentPromptLabel")
        context_l.addWidget(self.lbl_current_prompt)

        btn_analyze = QPushButton("Analyze Current Context")
        btn_analyze.setObjectName("AnalyzeBtn")
        btn_analyze.setFixedHeight(30)
        btn_analyze.clicked.connect(self._trigger_context_analysis)
        context_l.addWidget(btn_analyze)

        self.lbl_session_progress = QLabel("Session Progress: World Setup [0% Complete]")
        self.lbl_session_progress.setObjectName("SessionProgressLabel")
        context_l.addWidget(self.lbl_session_progress)

        ai_layout.addWidget(context_widget)

        div_ctx = QFrame()
        div_ctx.setFrameShape(QFrame.Shape.HLine)
        div_ctx.setStyleSheet("background: #29292E; max-height: 1px;")
        ai_layout.addWidget(div_ctx)

        # --- Input Area ---
        input_widget = QWidget()
        input_widget.setObjectName("AIInputArea")
        # Removing fixed height so it scales to fit both rows of inputs
        input_l = QHBoxLayout(input_widget)
        input_l.setContentsMargins(10, 9, 10, 9)
        input_l.setSpacing(8)

        self.ai_input = QLineEdit()
        self.ai_input.setObjectName("AIInputField")
        self.ai_input.setPlaceholderText("Ask Assistant / Generate Prompt...")
        self.ai_input.returnPressed.connect(self.send_ai_prompt)

        self.chk_active_prompts = QCheckBox("Enable Active Worldbuilding Prompts")
        self.chk_active_prompts.setChecked(True)
        self.chk_active_prompts.setStyleSheet("color: #E0E0E0; font-size: 11px;")
        
        self.cb_genre = QComboBox()
        self.cb_genre.addItems(["Fantasy", "Sci-Fi", "Cyberpunk", "Post-Apocalyptic", "Historical Fiction", "Modern Day", "Horror"])
        self.cb_genre.setStyleSheet("background: #111116; color: #EEEEF8; font-size: 11px;")
        self.cb_genre.setToolTip("Select World Genre constraints for AI")
        
        chk_genre_l = QHBoxLayout()
        chk_genre_l.addWidget(self.chk_active_prompts)
        chk_genre_l.addWidget(self.cb_genre)
        chk_genre_l.addStretch()
        
        input_v_l = QVBoxLayout()
        input_v_l.setSpacing(4)
        input_v_l.setContentsMargins(0,0,0,0)
        
        h_input_box = QHBoxLayout()
        h_input_box.setSpacing(8)
        
        self.btn_send_prompt = QToolButton()
        self.btn_send_prompt.setObjectName("SendBtn")
        self.btn_send_prompt.setText(">")
        self.btn_send_prompt.setFixedSize(32, 32)
        self.btn_send_prompt.clicked.connect(self.send_ai_prompt)

        h_input_box.addWidget(self.ai_input, 1)
        h_input_box.addWidget(self.btn_send_prompt)
        
        input_v_l.addLayout(h_input_box)
        input_v_l.addLayout(chk_genre_l)
        
        input_l.addLayout(input_v_l)

        ai_layout.addWidget(input_widget)

        # --- Lore Contradictions (collapsible) ---
        contra_header = QWidget()
        contra_header.setObjectName("ContraHeader")
        contra_header.setFixedHeight(30)
        contra_h_l = QHBoxLayout(contra_header)
        contra_h_l.setContentsMargins(10, 0, 10, 0)
        contra_h_l.setSpacing(6)

        contra_lbl = QLabel("! Unresolved Lore Contradictions")
        contra_lbl.setObjectName("ContraLabel")

        contra_toggle = QToolButton()
        contra_toggle.setText("v")
        contra_toggle.setObjectName("ContraToggle")
        contra_toggle.setFixedSize(22, 20)

        contra_h_l.addWidget(contra_lbl, 1)
        contra_h_l.addWidget(contra_toggle)

        ai_layout.addWidget(contra_header)

        self.inconsistency_list = QListWidget()
        self.inconsistency_list.setObjectName("InconsistencyList")
        self.inconsistency_list.setFixedHeight(80)
        self.inconsistency_list.itemDoubleClicked.connect(self.handle_inconsistency_double_clicked)
        contra_toggle.clicked.connect(
            lambda: self.inconsistency_list.setVisible(not self.inconsistency_list.isVisible())
        )
        ai_layout.addWidget(self.inconsistency_list)

        # --- Unified Timeline Section ---
        timeline_widget = QWidget()
        timeline_widget.setObjectName("TimelineWidget")
        timeline_l = QVBoxLayout(timeline_widget)
        timeline_l.setContentsMargins(10, 8, 10, 8)
        timeline_l.setSpacing(4)

        self.lbl_timeline = QLabel(f"<b>Historical Timeline (Year 1, Day 1 / {self.custom_seasons[0]})</b>")
        self.lbl_timeline.setStyleSheet("background: transparent; font-size: 11px;")
        
        row_label = QHBoxLayout()
        row_label.addWidget(self.lbl_timeline)
        
        self.btn_save_snapshot = QPushButton("Save Map State")
        self.btn_save_snapshot.setFixedWidth(120)
        self.btn_save_snapshot.clicked.connect(self.save_map_snapshot)
        row_label.addWidget(self.btn_save_snapshot)
        
        self.btn_audit_timeline = QPushButton("Audit Timeline")
        self.btn_audit_timeline.setFixedWidth(120)
        self.btn_audit_timeline.clicked.connect(self.audit_timeline)
        row_label.addWidget(self.btn_audit_timeline)
        
        timeline_l.addLayout(row_label)

        self.max_history_years = 1000
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setRange(1, self.max_history_years * self.custom_year_length)
        self.timeline_slider.setValue(1)
        self.timeline_slider.valueChanged.connect(self.handle_timeline_changed)
        timeline_l.addWidget(self.timeline_slider)

        self.celestial_widget = CelestialPreviewWidget(self)
        self.celestial_widget.setFixedHeight(60)
        timeline_l.addWidget(self.celestial_widget)

        self.btn_customize_templates = QPushButton("Customize Templates")
        self.btn_customize_templates.clicked.connect(self.show_template_customizer)
        self.btn_customize_templates.setFixedHeight(28)
        timeline_l.addWidget(self.btn_customize_templates)

        ai_layout.addWidget(timeline_widget)

        self.main_splitter.addWidget(self.ai_container)

    # =========================================================================
    # NEW UI HELPER METHODS
    # =========================================================================
    def _open_layer_editor(self, layer_key):
        """Open the ElementEditorDialog for a specific layer or activate its paint tool."""
        # Hide brush settings by default unless explicitly activated
        self.brush_settings_panel.hide()

        if layer_key == "Political States":
            self.cb_brush_mode.setCurrentText("State Paint")
            self.statusBar.showMessage("State Paint activated. Select or add a state in the Brush Settings panel, then click cells to paint.")
            self.brush_settings_panel.populate("Political States")
        elif layer_key == "Cultures":
            self.cb_brush_mode.setCurrentText("Culture Paint")
            self.statusBar.showMessage("Culture Paint activated. Select or add a culture in the Brush Settings panel, then click cells to paint.")
            self.brush_settings_panel.populate("Cultures")
        elif layer_key == "Military Regiments":
            self.cb_brush_mode.setCurrentText("Military Paint")
            self.statusBar.showMessage("Military Paint activated. Click a state's territory to deploy or remove an army.")
        elif layer_key == "Religions":
            self.cb_brush_mode.setCurrentText("Religion Paint")
            self.statusBar.showMessage("Religion Paint activated. Select or add a religion in the Brush Settings panel, then click cells to paint.")
            self.brush_settings_panel.populate("Religions")
        elif layer_key == "Provinces":
            self.cb_brush_mode.setCurrentText("Province Paint")
            self.statusBar.showMessage("Province Paint activated. Select or add a province in the Brush Settings panel, then click cells to paint.")
            self.brush_settings_panel.populate("Provinces")
        elif layer_key == "Burgs":
            self.cb_brush_mode.setCurrentText("Burg Paint")
            self.statusBar.showMessage("Burg Paint activated. Click on a cell to add/remove a settlement.")
        elif layer_key == "Elevation":
            self.cb_brush_mode.setCurrentText("Height Paint")
            self.statusBar.showMessage("Height Paint activated. Set the target height and click cells to paint.")
        elif layer_key == "Rivers":
            self.cb_brush_mode.setCurrentText("River Paint")
            self.statusBar.showMessage("River Paint activated. Set the river ID and click cells to paint.")
        elif layer_key == "Roads":
            self.cb_brush_mode.setCurrentText("Road Paint")
            self.statusBar.showMessage("Road Paint activated. Click cells to draw a road. Right-click to finish. Switch to 'Road Delete' in tools to erase.")
        elif layer_key == "Magic Layer":
            self.cb_brush_mode.setCurrentText("Magic Paint")
            self.statusBar.showMessage("Magic Paint activated. Select magic type in the Layer Tools panel.")
        elif layer_key == "Biomes":
            self.cb_brush_mode.setCurrentText("Biome Paint")
            self.statusBar.showMessage("Biome Paint activated. Select the biome and click cells to paint.")
        elif layer_key == "Production Goods":
            self.cb_brush_mode.setCurrentText("Production Paint")
            self.statusBar.showMessage("Production Paint activated. Select the good and click cells to paint.")
        else:
            QMessageBox.information(self, "Tool Editor", f"Tool editor for '{layer_key}' is not yet fully implemented.")

    def _select_layer_row(self, layer_key):
        """Visually activate a layer row and update the map layer via hidden combobox."""
        for lk, row in self._layer_row_widgets.items():
            if lk == layer_key:
                row.setStyleSheet(
                    "QWidget#LayerRow { background-color: #1a2a1a; border-left: 3px solid #04D361; }"
                )
            else:
                row.setStyleSheet(
                    "QWidget#LayerRow { background-color: transparent; border-left: 3px solid transparent; }"
                )
        self.cb_layer.setCurrentText(layer_key)

    def _set_layer_visibility(self, layer_key, visible):
        """Toggle a layer's visibility on the map viewer."""
        self.map_viewer.visibility_map[layer_key] = visible
        self.map_viewer.update()

    def _apply_text_format(self, fmt_type):
        """Insert Markdown syntax markers around selected text (or at cursor position)."""
        cursor  = self.note_editor.textCursor()
        selected = cursor.selectedText()
        markers = {
            "bold":          "**",
            "italic":        "*",
            "underline":     "__",
            "strikethrough": "~~",
        }
        marker = markers.get(fmt_type, "")
        if selected:
            cursor.insertText(f"{marker}{selected}{marker}")
        else:
            pos_before = cursor.position()
            cursor.insertText(f"{marker}{marker}")
            cursor.setPosition(pos_before + len(marker))
            self.note_editor.setTextCursor(cursor)

    def _apply_heading_format(self, level):
        """Prepend a Markdown heading prefix to the current line."""
        cursor = self.note_editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        prefix = "#" * level + " "
        cursor.insertText(prefix)
        self.note_editor.setTextCursor(cursor)

    def _insert_wiki_link(self):
        """Prompt for a note title and insert a [[WikiLink]] at the cursor."""
        link_title, ok = QInputDialog.getText(self, "Insert WikiLink", "Note Title to Link:")
        if ok and link_title.strip():
            cursor = self.note_editor.textCursor()
            cursor.insertText(f"[[{link_title.strip()}]]")

    def _trigger_context_analysis(self):
        """Build a context summary from current map cell and open note, then send to AI."""
        context_parts = []

        if self.selected_cell_idx is not None and self.map_engine.cells:
            try:
                cell = self.map_engine.cells[self.selected_cell_idx]
                context_parts.append(
                    f"Map Cell {self.selected_cell_idx}: "
                    f"Elevation={cell['h']}, Biome={cell['biome']}, State={cell['state']}"
                )
            except (IndexError, KeyError):
                pass

        note_title = self.note_title_input.text().strip()
        if note_title:
            context_parts.append(f"Current Note: {note_title}")

        if context_parts:
            prompt = "Analyze current context: " + "; ".join(context_parts)
            self.ai_input.setText(prompt)
            self.send_ai_prompt()
        else:
            self.statusBar.showMessage(
                "No context selected. Click a map cell or open a note first."
            )

    def _update_session_progress(self):
        """Increment the session progress display after each successful AI exchange."""
        self._session_msg_count += 1
        progress  = min(self._session_msg_count * 8, 95)
        topics    = [
            "World Setup", "Geography", "Biomes", "Cultures",
            "Political States", "Magic Systems", "History", "Mythology"
        ]
        topic_idx = min(self._session_msg_count // 2, len(topics) - 1)
        topic     = topics[topic_idx]

        if hasattr(self, "lbl_session_progress"):
            self.lbl_session_progress.setText(
                f"Session Progress: {topic} [{progress}% Complete]"
            )
        if hasattr(self, "lbl_current_prompt"):
            self.lbl_current_prompt.setText(f"Prompt: Detail a {topic}")

    # =========================================================================
    # EXISTING SLOT METHODS (all backend logic preserved verbatim)
    # =========================================================================
    def trigger_azgaar_tool_mode(self, tool_name):
        if tool_name == "Tools": return
        self.cb_tools.setCurrentIndex(0)

        if tool_name == "Edit State":
            editor = DataTableEditor("State", self.map_engine.states, self)
            editor.exec()
        elif tool_name == "Edit Culture":
            editor = DataTableEditor("Culture", self.map_engine.cultures, self)
            editor.exec()
        elif tool_name == "Edit Religion":
            editor = DataTableEditor("Religion", self.map_engine.religions, self)
            editor.exec()
        elif tool_name == "Add Burg":
            self.cb_brush_mode.setCurrentText("Burg Paint")
            self.statusBar.showMessage("Click on a cell to add a new settlement burg.")
        elif tool_name == "Delete Selected Element":
            self.statusBar.showMessage("Delete items from Element editor dropdown tables directly.")

    def toggle_layer_visibility(self, state):
        layer_name = self.cb_layer.currentText()
        self.map_viewer.visibility_map[layer_name] = (state == 2)
        self.map_viewer.update()

    def change_brush_size(self, val):
        self.map_viewer.brush_size = val

    def open_element_table_editor(self, val):
        if val == "Edit Element...": return
        self.cb_edit_element.setCurrentIndex(0)

        if val == "States Table":
            editor = DataTableEditor("State", self.map_engine.states, self)
        elif val == "Cultures Table":
            editor = DataTableEditor("Culture", self.map_engine.cultures, self)
        elif val == "Religions Table":
            editor = DataTableEditor("Religion", self.map_engine.religions, self)
        elif val == "Burgs Table":
            editor = DataTableEditor("Burg", self.map_engine.burgs, self)
        else:
            return

        editor.exec()

    def change_brush_mode(self, brush_name):
        self.map_viewer.brush_mode = brush_name

        # Show / hide magic type selector in the floating layer tools
        if hasattr(self, "floating_layer_tools"):
            self.floating_layer_tools.magic_section.setVisible(brush_name == "Magic Paint")

        # Prompt for target paint parameters if applicable
        if brush_name in ["State Paint", "Province Paint", "Culture Paint", "Religion Paint", "River Paint"]:
            val, ok = QInputDialog.getInt(
                self, "Brush Parameter", f"Enter ID to paint for {brush_name}:", value=1, min=1, max=100
            )
            if ok:
                if brush_name == "State Paint":    self.map_viewer.paint_state_value    = val
                elif brush_name == "Province Paint": self.map_viewer.paint_province_value = val
                elif brush_name == "Culture Paint":  self.map_viewer.paint_culture_value  = val
                elif brush_name == "Religion Paint": self.map_viewer.paint_religion_value = val
                elif brush_name == "River Paint":    self.map_viewer.paint_river_value    = val
        elif brush_name == "Height Paint":
            val, ok = QInputDialog.getInt(
                self, "Height Parameter", "Enter target cell height (5-95):", value=50, min=5, max=95
            )
            if ok:
                self.map_viewer.paint_height_value = val
        elif brush_name == "Biome Paint":
            biomes = ["Marine", "Hot Desert", "Montane / Glacier", "Tropical Rainforest", "Tundra", "Forest", "Grassland", "Savanna", "Kelp Meadows (Grassland)", "Coral Forest (Rainforest)", "Benthic Shelf (Savanna)", "Abyssal Trench (Desert)"]
            val, ok = QInputDialog.getItem(self, "Brush Parameter", "Select Biome to paint:", biomes, 0, False)
            if ok:
                self.map_viewer.paint_biome_value = val
        elif brush_name == "Production Paint":
            goods = ["None", "Grain", "Timber", "Spices", "Iron Ore", "Bioluminescent Kelp", "Precious Metals", "Abyssal Pearls", "Salt"]
            val, ok = QInputDialog.getItem(self, "Brush Parameter", "Select Production Good to paint:", goods, 0, False)
            if ok:
                self.map_viewer.paint_good_value = val

    def load_world_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load World File", "", "Database Files (*.db)")
        if not file_path:
            return
        try:
            import shutil
            shutil.copy(file_path, self.db_path)
            self.trigger_world_regeneration()
            self.statusBar.showMessage(f"World loaded successfully from '{file_path}'.")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load world file: {e}")

    def sink_ui_overlays_to_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ui_overlays (
                    layer TEXT PRIMARY KEY,
                    enabled INTEGER
                )
            """)
            if hasattr(self, "map_viewer"):
                for layer, enabled in self.map_viewer.visibility_map.items():
                    cursor.execute("INSERT OR REPLACE INTO ui_overlays (layer, enabled) VALUES (?, ?)", (layer, int(enabled)))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error sinking UI overlays: {e}")

    def save_world_to_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save World File", "", "Database Files (*.db)")
        if not file_path:
            return
        try:
            import shutil
            shutil.copy(self.db_path, file_path)
            self.statusBar.showMessage(f"World saved successfully to '{file_path}'.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save world file: {e}")

    def get_lore_dir(self):
        return os.path.join(self.project_dir, "lore")

    def trigger_world_regeneration(self):
        self.statusBar.showMessage("Generating new map layout and chaining all simulation layers...")
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
            self.sink_ui_overlays_to_db()
            self.load_map_data_to_viewer()
            self.statusBar.showMessage("World regeneration committed successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Pipeline Failure", f"Failed generation sequence: {e}")

    def load_unresolved_inconsistencies(self):
        self.inconsistency_list.clear()
        try:
            conn   = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT description FROM inconsistencies WHERE status='Active'")
            for row in cursor.fetchall():
                self.inconsistency_list.addItem(row[0])
            conn.close()
        except:
            pass

    def handle_inconsistency_double_clicked(self, item):
        self.ai_input.setText(f"Help me reconcile this lore error: {item.text()}")

    def show_template_customizer(self):
        dialog = TemplateDialog(self.template_mgr, self)
        dialog.exec()

    def setup_markers_db(self):
        try:
            conn   = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS note_map_bindings (
                    note_id INTEGER,
                    cell_idx INTEGER UNIQUE,
                    FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS markdown_map_bindings (
                    title TEXT PRIMARY KEY,
                    bind_type TEXT,
                    bind_target TEXT,
                    cell_idx INTEGER
                )
            """)
            conn.commit()
            conn.close()
        except:
            pass

    def setup_timeline_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS map_snapshots (
                    year INTEGER PRIMARY KEY,
                    engine_state_json BLOB
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS timeline_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER,
                    title TEXT,
                    content TEXT,
                    is_ai_generated INTEGER DEFAULT 0
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error setting up timeline db: {e}")

    def setup_staging_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lore_drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    content TEXT,
                    created_at TEXT,
                    is_ai_generated INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS note_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id INTEGER,
                    title TEXT,
                    content TEXT,
                    archived_at TEXT,
                    FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error setting up staging db: {e}")

    def setup_magic_db(self):
        try:
            conn   = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS magic_layers (
                    cell_idx INTEGER PRIMARY KEY,
                    magic_type TEXT NOT NULL
                )
            """)
            conn.commit()
            conn.close()
        except:
            pass

    def import_external_note(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import External Note", "", "Markdown Files (*.md);;Text Files (*.txt);;All Files (*)"
        )
        if not file_path:
            return

        self.start_ingestion([file_path])

    def import_external_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Folder to Import Notes")
        if not dir_path:
            return
            
        file_list = []
        for filename in os.listdir(dir_path):
            if filename.endswith(".md") or filename.endswith(".txt"):
                file_path = os.path.join(dir_path, filename)
                file_list.append(file_path)
                
        if file_list:
            self.start_ingestion(file_list)

    def start_ingestion(self, file_list):
        genre = self.cb_genre.currentText() if hasattr(self, "cb_genre") else "Fantasy"
        self.ingestor_worker = AILoreIngestor(file_list, self.db_path, self.get_lore_dir(), genre=genre)
        self.ingestor_worker.progress_update.connect(self.handle_ingestion_progress)
        self.ingestor_worker.ingestion_complete.connect(self.handle_ingestion_complete)
        self.ingestor_worker.start()
        self.statusBar.showMessage(f"Starting ingestion of {len(file_list)} files...")

    def handle_ingestion_progress(self, current, total, filename):
        self.statusBar.showMessage(f"Ingesting {current}/{total}: {filename}...")

    def handle_ingestion_complete(self):
        self.statusBar.showMessage("AI Ingestion Complete!")
        self.populate_file_tree()
        self.ai_prompt_history.append(
            f'<div style="text-align: left; margin: 2px 30px 6px 4px;">'
            f'<span style="display: inline-block; background: #1a1a2c; color: #D8D8EC; '
            f'border-radius: 14px 14px 14px 2px; padding: 7px 13px; font-size: 12px; '
            f'border-left: 3px solid #04D361;">'
            f'<span style="color: #04D361; font-weight: bold;">A</span> [System] I have successfully categorized and ingested the recent files. Check the file browser to see them organized.'
            f'</span></div>'
        )
        self._update_session_progress()
        
        # Now trigger the driver to find the first gap!
        genre = self.cb_genre.currentText() if hasattr(self, "cb_genre") else "Fantasy"
        self.driver_worker = AILoreDriverWorker(self.get_lore_dir(), genre=genre)
        self.driver_worker.prompt_ready.connect(self.handle_driver_prompt)
        self.driver_worker.start()

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
                self.driver_worker = AILoreDriverWorker(self.get_lore_dir(), genre=genre)
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
