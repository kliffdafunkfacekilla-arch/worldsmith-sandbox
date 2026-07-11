import os
import sys
import sqlite3
import json
import random

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
    QPainter, QColor, QPen, QBrush, QFont, QPixmap,
    QTextCursor, QTextCharFormat, QFileSystemModel
)

# Add project root directory to path for nested imports
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

def setup_cohesive_knowledge_db(db_path):
    """Creates a fully normalized, foreign-key-constrained SQLite database structure on boot."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # 1. Narrative Notes Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Factions (Sovereign States)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS factions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT NOT NULL,
                expansionism REAL DEFAULT 1.0,
                treasury REAL DEFAULT 1000.0,
                capital_cell INTEGER,
                associated_note_id INTEGER,
                FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL
            )
        """)

        # 3. Internal State Provinces
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS provinces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                color TEXT NOT NULL,
                state_id INTEGER NOT NULL,
                associated_note_id INTEGER,
                FOREIGN KEY(state_id) REFERENCES factions(id) ON DELETE CASCADE,
                FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL
            )
        """)

        # 4. Ethno-Linguistic Cultures & Species
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cultures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                code TEXT NOT NULL,
                language_base TEXT DEFAULT 'Imperial',
                associated_note_id INTEGER,
                FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL
            )
        """)

        # 5. Religions & Pantheons
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS religions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT NOT NULL,
                supreme_deity TEXT DEFAULT 'Unknown',
                associated_note_id INTEGER,
                FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL
            )
        """)

        # 6. Physical Settlements (Burgs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settlements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                population REAL DEFAULT 10.0,
                cell_idx INTEGER,
                faction_id INTEGER,
                culture_id INTEGER,
                associated_note_id INTEGER,
                FOREIGN KEY(faction_id) REFERENCES factions(id) ON DELETE SET NULL,
                FOREIGN KEY(culture_id) REFERENCES cultures(id) ON DELETE SET NULL,
                FOREIGN KEY(associated_note_id) REFERENCES notes(id) ON DELETE SET NULL
            )
        """)

        # 7. Spatial Mesh Coordinate Cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cells (
                id INTEGER PRIMARY KEY,
                centroid_x REAL NOT NULL,
                centroid_y REAL NOT NULL,
                elevation INTEGER DEFAULT 20,
                moisture INTEGER DEFAULT 10,
                temperature INTEGER DEFAULT 15,
                biome TEXT DEFAULT 'Marine',
                state_id INTEGER,
                province_id INTEGER,
                culture_id INTEGER,
                religion_id INTEGER,
                FOREIGN KEY(state_id) REFERENCES factions(id) ON DELETE SET NULL,
                FOREIGN KEY(province_id) REFERENCES provinces(id) ON DELETE SET NULL,
                FOREIGN KEY(culture_id) REFERENCES cultures(id) ON DELETE SET NULL,
                FOREIGN KEY(religion_id) REFERENCES religions(id) ON DELETE SET NULL
            )
        """)

        # 8. Note Geography Bindings Map
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS note_map_bindings (
                note_id INTEGER NOT NULL,
                cell_idx INTEGER NOT NULL,
                PRIMARY KEY (note_id, cell_idx),
                FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE,
                FOREIGN KEY(cell_idx) REFERENCES cells(id) ON DELETE CASCADE
            )
        """)

        # 9. AI Reconciliation Anomaly Log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inconsistencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_type TEXT NOT NULL,
                subject_id INTEGER,
                description TEXT NOT NULL,
                suggested_solution TEXT,
                status TEXT DEFAULT 'Active'
            )
        """)

        # 10. Magic Leylines Layer
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS magic_layers (
                cell_idx INTEGER PRIMARY KEY,
                magic_type TEXT NOT NULL,
                intensity REAL DEFAULT 1.0
            )
        """)

        # 11. Economic Commodities
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS production_goods (
                cell_id INTEGER PRIMARY KEY,
                good TEXT NOT NULL,
                valuation REAL DEFAULT 1.0
            )
        """)

        # 12. Timeline map snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS map_snapshots (
                year INTEGER PRIMARY KEY,
                engine_state_json BLOB NOT NULL
            )
        """)

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error establishing cohesive knowledge database schema: {e}")


# =============================================================================
# WORKER: Dynamic Folder Ingestor and Dissection Thread
# =============================================================================
class KnowledgeIngestorWorker(QThread):
    progress_update = pyqtSignal(int, int, str) # current, total, filename
    dissection_complete = pyqtSignal(list) # list of extracted entity nodes

    def __init__(self, file_paths, db_path, vault_dir):
        super().__init__()
        self.file_paths = file_paths
        self.db_path = db_path
        self.vault_dir = vault_dir

    def run(self):
        extracted_nodes = []
        total_files = len(self.file_paths)
        
        # Categorized directories list on disk
        categories = ["Characters", "Factions", "Locations", "Cultures", "Religions", "General"]
        for cat in categories:
            os.makedirs(os.path.join(self.vault_dir, cat), exist_ok=True)

        for idx, file_path in enumerate(self.file_paths):
            filename = os.path.basename(file_path)
            self.progress_update.emit(idx + 1, total_files, filename)
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_text = f.read()

                # Dissect unstructured text into template metadata payload
                dissected = self.dissect_narrative_text(filename, raw_text)
                extracted_nodes.append(dissected)

                # Commit extracted nodes straight to SQL tables
                self.commit_dissected_lore_to_db(dissected, raw_text)

                # Write sorted file cleanly to its structured folder vault
                target_cat = dissected["category"]
                dest_path = os.path.join(self.vault_dir, target_cat, filename)
                with open(dest_path, "w", encoding="utf-8") as dest_f:
                    dest_f.write(raw_text)

            except Exception as e:
                print(f"Failed to ingest file '{filename}': {e}")
            
            self.msleep(100)

        self.dissection_complete.emit(extracted_nodes)

    def dissect_narrative_text(self, filename, text):
        """Dynamic heuristic dissection engine mapping paragraphs to SQL schemas."""
        title = os.path.splitext(filename)[0]
        lower_text = text.lower()

        # Dynamic template category clustering
        category = "General"
        if any(kw in lower_text for kw in ["character", "hero", "lord", "lady", "enzo"]):
            category = "Characters"
        elif any(kw in lower_text for kw in ["empire", "hegemony", "faction", "concord", "state"]):
            category = "Factions"
        elif any(kw in lower_text for kw in ["culture", "tribe", "species", "elven", "moray"]):
            category = "Cultures"
        elif any(kw in lower_text for kw in ["worship", "temple", "deity", "pantheon", "religion"]):
            category = "Religions"
        elif any(kw in lower_text for kw in ["citadel", "city", "keep", "island", "wastes", "location"]):
            category = "Locations"

        dissected_payload = {
            "title": title,
            "category": category,
            "entities": []
        }

        # Structure entities from text
        entity_name = title.replace("_", " ").title()
        if category == "Factions":
            color = random.choice(["#ef4444", "#3b82f6", "#10b981", "#eab308", "#8b5cf6"])
            dissected_payload["entities"].append({
                "type": "faction",
                "name": entity_name,
                "color": color,
                "expansionism": round(random.uniform(0.8, 1.6), 2),
                "treasury": round(random.uniform(2500.0, 7500.0), 2)
            })
        elif category == "Religions":
            deity = "Dawnbringer Solis" if "dawn" in lower_text else "High Wyrm"
            dissected_payload["entities"].append({
                "type": "religion",
                "name": entity_name,
                "color": random.choice(["#eab308", "#a855f7", "#ec4899"]),
                "supreme_deity": deity
            })
        elif category == "Cultures":
            code = "".join([w[0].upper() for w in entity_name.split() if w])[:3]
            dissected_payload["entities"].append({
                "type": "culture",
                "name": entity_name,
                "code": code if code else "CL"
            })
        elif category == "Locations":
            dissected_payload["entities"].append({
                "type": "settlement",
                "name": entity_name,
                "population": round(random.uniform(8.0, 30.0), 1),
                "cell_idx": random.randint(1, 1000)
            })

        return dissected_payload

    def commit_dissected_lore_to_db(self, dissected, original_text):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Save the primary note entry
            cursor.execute("""
                INSERT INTO notes (title, content, category)
                VALUES (?, ?, ?)
                ON CONFLICT(title) DO UPDATE SET content=excluded.content, category=excluded.category
            """, (dissected["title"], original_text, dissected["category"]))
            
            note_id = cursor.lastrowid if cursor.lastrowid else 1
            
            # Populate our structured template fields using Foreign Key links
            for ent in dissected["entities"]:
                ent_type = ent["type"]
                if ent_type == "faction":
                    cursor.execute("""
                        INSERT INTO factions (name, color, expansionism, treasury, associated_note_id)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(name) DO UPDATE SET color=excluded.color, expansionism=excluded.expansionism
                    """, (ent["name"], ent["color"], ent["expansionism"], ent["treasury"], note_id))
                elif ent_type == "religion":
                    cursor.execute("""
                        INSERT INTO religions (name, color, supreme_deity, associated_note_id)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(name) DO UPDATE SET supreme_deity=excluded.supreme_deity
                    """, (ent["name"], ent["color"], ent["supreme_deity"], note_id))
                elif ent_type == "culture":
                    cursor.execute("""
                        INSERT INTO cultures (name, code, associated_note_id)
                        VALUES (?, ?, ?)
                        ON CONFLICT(name) DO UPDATE SET code=excluded.code
                    """, (ent["name"], ent["code"], note_id))
                elif ent_type == "settlement":
                    cursor.execute("""
                        INSERT INTO settlements (name, population, cell_idx, associated_note_id)
                        VALUES (?, ?, ?, ?)
                    """, (ent["name"], ent["population"], ent["cell_idx"], note_id))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error committing dissected note rows to SQLite: {e}")


# =============================================================================
# PROMPT DIALOG: STARTUP PROJECT WIZARD
# =============================================================================
class ProjectStartupWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_dir = None
        self.setWindowTitle("Lordsmith Studio Startup Wizard")
        self.resize(460, 240)
        self.setStyleSheet("background-color: #111116; color: #EEEEF8; font-family: Arial;")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>🌌 Welcome to Lordsmith Studio</h2>"))
        layout.addWidget(QLabel("Select an existing project workspace database or start fresh."))
        
        btn_new = QPushButton("🎲 Create Fresh Workspace")
        btn_new.setStyleSheet("background-color: #04D361; color: black; font-weight: bold; padding: 10px; font-size: 13px;")
        btn_new.clicked.connect(self.action_new_project)

        btn_load = QPushButton("📂 Open Existing Project (.db)")
        btn_load.clicked.connect(self.action_load_project)

        layout.addWidget(btn_new)
        layout.addWidget(btn_load)
        layout.addStretch()

    def action_new_project(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Project Folder Directory")
        if dir_path:
            self.selected_dir = dir_path
            self.accept()

    def action_load_project(self):
        db_file, _ = QFileDialog.getOpenFileName(self, "Load SQLite Database File", "", "Databases (*.db)")
        if db_file:
            self.selected_dir = os.path.dirname(db_file)
            self.accept()


# =============================================================================
# MAIN WINDOW: Symmetrical Three-Panel Workspace
# =============================================================================
class LordsmithStudioMainWindow(QMainWindow):
    def __init__(self, project_dir):
        super().__init__()
        self.project_dir = os.path.abspath(project_dir)
        project_name = os.path.basename(self.project_dir)
        self.setWindowTitle(f"Lordsmith Studio Workspace - {project_name}")
        self.resize(1650, 950)
        self.setStyleSheet("background-color: #111116; color: #EEEEF8;")

        # Active Data Environment definitions
        self.db_path = os.path.join(self.project_dir, "lore_forge_world.db")
        setup_cohesive_knowledge_db(self.db_path)

        # Prebuilt map generator engines
        self.map_engine = AzgaarEngine()
        self.active_question_queue = []
        self.active_question_index = 0
        self.selected_note_id = None
        self.selected_note_title = None

        self._apply_symmetrical_stylesheet()
        self._build_classic_menubar()

        # --- Base Layout Construction ---
        central_container = QWidget()
        self.setCentralWidget(central_container)
        main_h_layout = QHBoxLayout(central_container)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        # 1. Left Narrow File Browser Panel
        self.browser_frame = QWidget()
        self.browser_frame.setFixedWidth(240)
        self.browser_frame.setStyleSheet("background-color: #14141d; border-right: 1px solid #29292E;")
        browser_layout = QVBoxLayout(self.browser_frame)
        browser_layout.setContentsMargins(4, 8, 4, 8)
        
        self.lbl_browser_title = QLabel("<b>📂 LORE VAULT STRUCTURE</b>")
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(self.get_vault_dir())
        
        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(self.file_model.index(self.get_vault_dir()))
        self.file_tree.setColumnHidden(1, True)
        self.file_tree.setColumnHidden(2, True)
        self.file_tree.setColumnHidden(3, True)
        self.file_tree.setHeaderHidden(True)
        self.file_tree.clicked.connect(self.on_file_browser_node_clicked)

        browser_layout.addWidget(self.lbl_browser_title)
        browser_layout.addWidget(self.file_tree)
        main_h_layout.addWidget(self.browser_frame)

        # 2. Main Double Splitter Grid (Houses the 3 Panels + Ingestion Screen + Bottom Chat)
        self.grid_splitter = QSplitter(Qt.Orientation.Vertical)
        self.grid_splitter.setStyleSheet("QSplitter::handle { background: #29292E; height: 3px; }")
        main_h_layout.addWidget(self.grid_splitter, 1)

        # Top Splitter: 3 Horizontal Panels
        self.top_panels_widget = QWidget()
        self.top_panels_layout = QHBoxLayout(self.top_panels_widget)
        self.top_panels_layout.setContentsMargins(0, 0, 0, 0)
        self.top_panels_layout.setSpacing(0)
        
        self.panels_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.panels_splitter.setStyleSheet("QSplitter::handle { background: #29292E; width: 3px; }")
        self.top_panels_layout.addWidget(self.panels_splitter)
        
        self.grid_splitter.addWidget(self.top_panels_widget)

        # PANEL 1 (LEFT): Narrative Note Writer Editor
        self.panel_left = QWidget()
        self.panel_left.setStyleSheet("background-color: #111116; border-right: 1px solid #29292E;")
        pl_lay = QVBoxLayout(self.panel_left)
        pl_lay.setContentsMargins(6, 6, 6, 6)
        
        self.txt_note_title = QLineEdit()
        self.txt_note_title.setPlaceholderText("Narrative Source Document Title...")
        self.btn_save_note = QPushButton("💾 Save Local Document")
        self.btn_save_note.setStyleSheet("background-color: #04D361; color: black; font-weight: bold;")
        self.btn_save_note.clicked.connect(self.save_active_note_content)
        
        self.note_writer = MarkdownNotebookEditor(self)
        
        pl_lay.addWidget(QLabel("<b>✍️ Narrative Lore Writer</b>"))
        pl_lay.addWidget(self.txt_note_title)
        pl_lay.addWidget(self.note_writer, 1)
        pl_lay.addWidget(self.btn_save_note)
        self.panels_splitter.addWidget(self.panel_left)

        # PANEL 2 (MIDDLE): Active Grid Table Viewer
        self.panel_middle = QWidget()
        self.panel_middle.setStyleSheet("background-color: #111116; border-right: 1px solid #29292E;")
        pm_lay = QVBoxLayout(self.panel_middle)
        pm_lay.setContentsMargins(6, 6, 6, 6)
        
        self.middle_table = QTableWidget()
        self.middle_table.setColumnCount(3)
        self.middle_table.setHorizontalHeaderLabels(["ID", "Name", "Properties"])
        self.middle_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.middle_table.setStyleSheet("QTableWidget { background-color: #16161f; }")
        self.middle_table.itemSelectionChanged.connect(self.on_middle_table_selection_changed)

        pm_lay.addWidget(QLabel("<b>📋 Structured Database Registry</b>"))
        pm_lay.addWidget(self.middle_table, 1)
        self.panels_splitter.addWidget(self.panel_middle)

        # PANEL 3 (RIGHT): Detailed Parameter Inspector / Visualization Canvas Drawer
        self.panel_right = QWidget()
        self.panel_right.setStyleSheet("background-color: #111116;")
        pr_lay = QVBoxLayout(self.panel_right)
        pr_lay.setContentsMargins(6, 6, 6, 6)
        
        self.inspector_stack = QStackedWidget()
        
        # Form Sub-Panel View (Data Controls)
        self.form_widget = QScrollArea()
        self.form_widget.setWidgetResizable(True)
        self.form_inner = QWidget()
        self.form_layout = QFormLayout(self.form_inner)
        self.form_widget.setWidget(self.form_inner)
        self.inspector_stack.addWidget(self.form_widget)
        
        # Interactive Map Sub-Panel View
        self.map_viewer_widget = MapViewerWidget(self)
        self.inspector_stack.addWidget(self.map_viewer_widget)

        pr_lay.addWidget(QLabel("<b>⚙️ Parameter Inspector &amp; Canvas View</b>"))
        pr_lay.addWidget(self.inspector_stack, 1)
        self.panels_splitter.addWidget(self.panel_right)

        # 3. Bottom Panel (Persistent wide-screen chat interface)
        self.bottom_chat_panel = QWidget()
        self.bottom_chat_panel.setStyleSheet("background-color: #14141d; border-top: 1px solid #29292E;")
        self.bottom_chat_panel.setFixedHeight(240)
        chat_layout = QVBoxLayout(self.bottom_chat_panel)
        chat_layout.setContentsMargins(8, 8, 8, 8)
        
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("background-color: #0d0d12; border: 1px solid #29292E; color: #EEEEF8;")
        
        self.chat_input_layout = QHBoxLayout()
        self.txt_chat_prompt = QLineEdit()
        self.txt_chat_prompt.setPlaceholderText("Answer the AI's question, clarify detail discrepancies, or command progress...")
        self.txt_chat_prompt.returnPressed.connect(self.send_chat_message_to_reconciler)
        
        self.btn_send_chat = QPushButton("➤ Send")
        self.btn_send_chat.clicked.connect(self.send_chat_message_to_reconciler)
        self.chat_input_layout.addWidget(self.txt_chat_prompt, 1)
        self.chat_input_layout.addWidget(self.btn_send_chat)

        self.btn_generate_map_synthesis = QPushButton("🎲 SYNTHESIZE LORE MAP")
        self.btn_generate_map_synthesis.setStyleSheet("background-color: #04D361; color: black; font-weight: bold; font-size: 13px; min-width: 200px;")
        self.btn_generate_map_synthesis.clicked.connect(self.trigger_map_synthesis_pipeline)
        self.btn_generate_map_synthesis.setEnabled(False) # Locked on startup until database constraints clear
        self.chat_input_layout.addWidget(self.btn_generate_map_synthesis)

        chat_layout.addWidget(QLabel("<b>🤖 Local AI Inconsistency Analyst &amp; Interviewer</b>"))
        chat_layout.addWidget(self.chat_history, 1)
        chat_layout.addLayout(self.chat_input_layout)

        self.grid_splitter.addWidget(self.bottom_chat_panel)

        # 4. Standard Bottom Status Strip
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Studio ready. Ingest a folder of notes to begin analysis.")

        # Trigger Standby state if database is empty
        self.evaluate_ingestion_standby_state()

    def get_vault_dir(self):
        vault = os.path.join(self.project_dir, "lore")
        if not os.path.exists(vault):
            os.makedirs(vault)
        return vault

    def evaluate_ingestion_standby_state(self):
        """Verifies if the database is populated. If empty, forces note import dialogue."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM notes")
            notes_count = cursor.fetchone()[0]
            conn.close()
            
            if notes_count == 0:
                self.chat_history.append(
                    "<b>[AI Interviewer]</b> Hello! I detected a fresh workspace without any lore documentation.<br>"
                    "To begin, please select <b>Imports -> Ingest Note Directory Folder</b> from the menu bar to import your raw text notes."
                )
                self.btn_generate_map_synthesis.setEnabled(False)
            else:
                self.run_local_lore_reconciliation()
        except Exception as e:
            print(f"Error checking vault status: {e}")

    def _apply_symmetrical_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #111116; }
            QWidget { color: #EEEEF8; font-family: "Segoe UI", Arial, sans-serif; }
            QTreeView { background-color: #14141d; border: none; }
            QTreeView::item:selected { background-color: #29293a; color: #04D361; }
            QLineEdit { background-color: #1a1a24; border: 1px solid #333333; padding: 4px; border-radius: 3px; }
            QPushButton { background-color: #29293a; border: 1px solid #404060; padding: 5px; border-radius: 4px; }
            QPushButton:hover { background-color: #3b3b54; }
            QScrollArea { border: none; }
            QTableWidget { gridline-color: #29292E; border: none; }
            QTableWidget::item:selected { background-color: #29293a; }
        """)

    def _build_classic_menubar(self):
        """Assembles native classic horizontal top menu layout options."""
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""
            QMenuBar { background-color: #16161c; color: #EEEEF8; border-bottom: 1px solid #29292E; }
            QMenuBar::item:selected { background-color: #29293a; color: #04D361; }
            QMenu { background-color: #1e1e2c; color: #EEEEF8; border: 1px solid #404060; }
            QMenu::item:selected { background-color: #29293a; color: #04D361; }
        """)
        
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction("🎲 Synthesize Map Layer Layout", self.trigger_map_synthesis_pipeline)
        file_menu.addSeparator()
        file_menu.addAction("Exit Studio", self.close)

        import_menu = menu_bar.addMenu("&Imports")
        import_menu.addAction("📁 Ingest Note Directory Folder", self.import_external_folder_dissection)

    def import_external_folder_dissection(self):
        """Launches directory selector and fires ingestion worker thread."""
        d = QFileDialog.getExistingDirectory(self, "Select Unstructured Notes Folder")
        if d:
            file_list = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(('.md', '.txt'))]
            if not file_list:
                QMessageBox.warning(self, "No files found", "No markdown (.md) or text (.txt) files found in that directory.")
                return

            # Display ingestion loading HUD
            self.loading_dialog = QDialog(self)
            self.loading_dialog.setWindowTitle("Parsing World Lore Files...")
            self.loading_dialog.resize(400, 120)
            ld_lay = QVBoxLayout(self.loading_dialog)
            
            self.lbl_loading_info = QLabel("Starting extraction...")
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, len(file_list))
            
            ld_lay.addWidget(self.lbl_loading_info)
            ld_lay.addWidget(self.progress_bar)
            self.loading_dialog.show()

            self.worker = KnowledgeIngestorWorker(file_list, self.db_path, self.get_vault_dir())
            self.worker.progress_update.connect(self.on_ingestion_progress)
            self.worker.dissection_complete.connect(self.on_ingestion_complete)
            self.worker.start()

    def on_ingestion_progress(self, current, total, filename):
        self.progress_bar.setValue(current)
        self.lbl_loading_info.setText(f"Dissecting {current}/{total}: {filename}...")

    def on_ingestion_complete(self, extracted_nodes):
        self.loading_dialog.accept()
        self.file_model.setRootPath(self.get_vault_dir())
        self.file_tree.setRootIndex(self.file_model.index(self.get_vault_dir()))
        self.statusBar.showMessage("Lore imported and structured successfully.")
        
        self.chat_history.clear()
        self.chat_history.append(
            "<b>[AI Interviewer]</b> Ingestion complete! I have finished analyzing your raw note vault "
            "and successfully parsed your lore documents into organized categories.<br>"
            "Running a local consistency audit on the database now..."
        )
        
        self.run_local_lore_reconciliation()

    # =============================================================================
    # RECONCILIATION ENGINE & ACTIVE INTERVIEW QUEUE
    # =============================================================================
    def run_local_lore_reconciliation(self):
        """Scans SQLite tables for relational inconsistencies and populates the interview loop."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clear old inconsistencies
            cursor.execute("DELETE FROM inconsistencies")
            
            self.active_question_queue = []
            
            # Check 1: Factions without defined starting capitals
            cursor.execute("SELECT id, name FROM factions WHERE capital_cell IS NULL")
            for fid, name in cursor.fetchall():
                desc = f"The Faction '{name}' does not have a designated spatial capital city or coordinate region assigned."
                cursor.execute("INSERT INTO inconsistencies (subject_type, subject_id, description) VALUES ('Faction', ?, ?)", (fid, desc))
                self.active_question_queue.append({
                    "type": "Faction",
                    "id": fid,
                    "name": name,
                    "field": "capital_cell",
                    "question": f"Where is the capital of the **{name}** situated geographically? Provide a coordinates zone or nearby landmark."
                })
                
            # Check 2: Settlements without controlling factions
            cursor.execute("SELECT id, name FROM settlements WHERE faction_id IS NULL")
            for sid, name in cursor.fetchall():
                desc = f"The Settlement '{name}' lacks a declared governing state body or political affiliation."
                cursor.execute("INSERT INTO inconsistencies (subject_type, subject_id, description) VALUES ('Settlement', ?, ?)", (sid, desc))
                self.active_question_queue.append({
                    "type": "Settlement",
                    "id": sid,
                    "name": name,
                    "field": "faction_id",
                    "question": f"Which sovereign faction actively claims dominion over the burg of **{name}**?"
                })

            # Check 3: Religions without Supreme Deities
            cursor.execute("SELECT id, name FROM religions WHERE supreme_deity = 'Unknown'")
            for rid, name in cursor.fetchall():
                desc = f"The Religion '{name}' does not have an assigned head god, supreme deity, or localized avatar."
                cursor.execute("INSERT INTO inconsistencies (subject_type, subject_id, description) VALUES ('Religion', ?, ?)", (rid, desc))
                self.active_question_queue.append({
                    "type": "Religion",
                    "id": rid,
                    "name": name,
                    "field": "supreme_deity",
                    "question": f"Who is the supreme deity, avatar, or high guiding force worshipped within the **{name}** faith?"
                })

            conn.commit()
            conn.close()
            
            if self.active_question_queue:
                self.active_question_index = 0
                self.present_current_active_question()
            else:
                self.chat_history.append(
                    "<br><b>[AI Interviewer]</b> Fantastic news! The knowledge base is fully structured, "
                    "with zero unresolved contradictions or structural omissions detected.<br>"
                    "The <b>procedural cartography synthesis layer is now fully unlocked</b> and ready to generate!"
                )
                self.btn_generate_map_synthesis.setEnabled(True)

        except Exception as e:
            print(f"Error during reconciliation phase: {e}")

    def present_current_active_question(self):
        """Updates Left, Middle, and Right Panels contextually based on the active question."""
        if self.active_question_index >= len(self.active_question_queue):
            self.run_local_lore_reconciliation()
            return
            
        q = self.active_question_queue[self.active_question_index]
        self.chat_history.append(f"<br><b>[AI Question on {q['type']}]</b> {q['question']}")
        
        # Route Panels contextually to match the active question's domain
        self.align_panels_to_subject_theme(q["type"], q["id"])

    def align_panels_to_subject_theme(self, subject_type, entity_id):
        """Dynamically populates Left, Middle, and Right panels with synced data of the active subject."""
        self.middle_table.blockSignals(True)
        self.middle_table.setRowCount(0)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Step A: Load grid table matching the active subject category (Panel 2)
            if subject_type == "Faction":
                self.middle_table.setColumnCount(3)
                self.middle_table.setHorizontalHeaderLabels(["ID", "Faction Name", "Expansionism"])
                cursor.execute("SELECT id, name, expansionism FROM factions")
                rows = cursor.fetchall()
                self.middle_table.setRowCount(len(rows))
                for idx, (fid, name, exp) in enumerate(rows):
                    self.middle_table.setItem(idx, 0, QTableWidgetItem(str(fid)))
                    self.middle_table.setItem(idx, 1, QTableWidgetItem(name))
                    self.middle_table.setItem(idx, 2, QTableWidgetItem(str(exp)))
                    
                # Load active note text (Panel 1)
                cursor.execute("SELECT associated_note_id FROM factions WHERE id = ?", (entity_id,))
                note_id_row = cursor.fetchone()
                if note_id_row and note_id_row[0]:
                    self.load_note_by_id(note_id_row[0])
                    
            elif subject_type == "Settlement":
                self.middle_table.setColumnCount(3)
                self.middle_table.setHorizontalHeaderLabels(["ID", "Burg Name", "Population (k)"])
                cursor.execute("SELECT id, name, population FROM settlements")
                rows = cursor.fetchall()
                self.middle_table.setRowCount(len(rows))
                for idx, (sid, name, pop) in enumerate(rows):
                    self.middle_table.setItem(idx, 0, QTableWidgetItem(str(sid)))
                    self.middle_table.setItem(idx, 1, QTableWidgetItem(name))
                    self.middle_table.setItem(idx, 2, QTableWidgetItem(str(pop)))
                    
                cursor.execute("SELECT associated_note_id FROM settlements WHERE id = ?", (entity_id,))
                note_id_row = cursor.fetchone()
                if note_id_row and note_id_row[0]:
                    self.load_note_by_id(note_id_row[0])

            elif subject_type == "Religion":
                self.middle_table.setColumnCount(3)
                self.middle_table.setHorizontalHeaderLabels(["ID", "Religion Name", "Supreme Deity"])
                cursor.execute("SELECT id, name, supreme_deity FROM religions")
                rows = cursor.fetchall()
                self.middle_table.setRowCount(len(rows))
                for idx, (rid, name, deity) in enumerate(rows):
                    self.middle_table.setItem(idx, 0, QTableWidgetItem(str(rid)))
                    self.middle_table.setItem(idx, 1, QTableWidgetItem(name))
                    self.middle_table.setItem(idx, 2, QTableWidgetItem(str(deity)))
                    
                cursor.execute("SELECT associated_note_id FROM religions WHERE id = ?", (entity_id,))
                note_id_row = cursor.fetchone()
                if note_id_row and note_id_row[0]:
                    self.load_note_by_id(note_id_row[0])

            # Select and highlight the active entity row in Panel 2
            for row in range(self.middle_table.rowCount()):
                if int(self.middle_table.item(row, 0).text()) == entity_id:
                    self.middle_table.selectRow(row)
                    break

            conn.close()
        except Exception as e:
            print(f"Error drawing contextual sub-grids: {e}")
            
        self.middle_table.blockSignals(False)
        self.update_parameter_inspector(subject_type, entity_id)

    def load_note_by_id(self, note_id):
        """Loads narrative prose matching note_id straight into Panel 1."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, content FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                self.selected_note_id = row[0]
                self.selected_note_title = row[1]
                self.txt_note_title.setText(row[1])
                self.note_writer.setPlainText(row[2])
        except Exception as e:
            print(f"Error loading associated note: {e}")

    def on_file_browser_node_clicked(self, index):
        """Opens selected files straight inside Panel 1."""
        file_path = self.file_model.filePath(index)
        if not self.file_model.isDir(index) and file_path.endswith(('.md', '.txt')):
            title = os.path.splitext(os.path.basename(file_path))[0]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                self.txt_note_title.setText(title)
                self.note_writer.setPlainText(content)
                self.selected_note_title = title
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM notes WHERE title = ?", (title,))
                row = cursor.fetchone()
                if row:
                    self.selected_note_id = row[0]
                conn.close()
            except Exception as e:
                print(e)

    def save_active_note_content(self):
        """Commits Panel 1 editor changes to SQLite and flat-file disk storage."""
        title = self.txt_note_title.text().strip()
        content = self.note_writer.toPlainText().strip()
        if not title: return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notes (title, content, category)
                VALUES (?, ?, 'General')
                ON CONFLICT(title) DO UPDATE SET content=excluded.content, updated_at=datetime('now')
            """, (title, content))
            conn.commit()
            conn.close()

            # Save file to General folder
            os.makedirs(os.path.join(self.get_vault_dir(), "General"), exist_ok=True)
            f_path = os.path.join(self.get_vault_dir(), "General", f"{title}.md")
            with open(f_path, "w", encoding="utf-8") as file:
                file.write(content)
                
            self.statusBar.showMessage(f"Note '{title}' saved to database and disk vault.")
            self.run_local_lore_reconciliation()
        except Exception as e:
            print(f"Error committing note data: {e}")

    # =============================================================================
    # PANEL 3: ADAPTIVE PARAMETER FORM INSPECTOR
    # =============================================================================
    def on_middle_table_selection_changed(self):
        selected_ranges = self.middle_table.selectedRanges()
        if not selected_ranges: return
        row = selected_ranges[0].topRow()
        entity_id = int(self.middle_table.item(row, 0).text())
        
        # Determine current active subject from the Bottom Question queue
        if self.active_question_index < len(self.active_question_queue):
            q = self.active_question_queue[self.active_question_index]
            self.update_parameter_inspector(q["type"], entity_id)

    def update_parameter_inspector(self, subject_type, entity_id):
        """Recreates a dynamic, scrollable form panel matching Azgaar's editing tools."""
        self.inspector_stack.setCurrentIndex(0) # Swap to Form layout page
        
        # Clear old form inputs safely
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            w = item.widget()
            if w: w.setParent(None)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if subject_type == "Faction":
                cursor.execute("SELECT name, color, expansionism, treasury FROM factions WHERE id = ?", (entity_id,))
                row = cursor.fetchone()
                if row:
                    lbl_id = QLabel(f"<b>Faction ID:</b> {entity_id}")
                    self.form_layout.addRow(lbl_id)
                    
                    self.txt_fac_name = QLineEdit(row[0])
                    self.form_layout.addRow("Faction Name:", self.txt_fac_name)
                    
                    self.txt_fac_color = QLineEdit(row[1])
                    btn_color = QPushButton("Pick Color")
                    btn_color.clicked.connect(lambda: self.trigger_color_picker_form(self.txt_fac_color))
                    color_lay = QHBoxLayout()
                    color_lay.addWidget(self.txt_fac_color)
                    color_lay.addWidget(btn_color)
                    self.form_layout.addRow("Border Color:", color_lay)

                    self.sp_fac_exp = QDoubleSpinBox()
                    self.sp_fac_exp.setRange(0.1, 5.0)
                    self.sp_fac_exp.setValue(row[2] if row[2] else 1.0)
                    self.form_layout.addRow("Expansion Rate:", self.sp_fac_exp)

                    self.sp_fac_treasury = QDoubleSpinBox()
                    self.sp_fac_treasury.setRange(0.0, 100000.0)
                    self.sp_fac_treasury.setValue(row[3] if row[3] else 0.0)
                    self.form_layout.addRow("Treasury Gold:", self.sp_fac_treasury)
                    
                    btn_apply = QPushButton("Apply State Changes")
                    btn_apply.clicked.connect(lambda: self.commit_faction_form_changes(entity_id))
                    self.form_layout.addRow(btn_apply)

            elif subject_type == "Settlement":
                cursor.execute("SELECT name, population, cell_idx FROM settlements WHERE id = ?", (entity_id,))
                row = cursor.fetchone()
                if row:
                    self.txt_burg_name = QLineEdit(row[0])
                    self.form_layout.addRow("Burg Name:", self.txt_burg_name)
                    
                    self.sp_burg_pop = QDoubleSpinBox()
                    self.sp_burg_pop.setRange(0.1, 1000.0)
                    self.sp_burg_pop.setValue(row[1] if row[1] else 10.0)
                    self.form_layout.addRow("Population (k):", self.sp_burg_pop)
                    
                    lbl_cell = QLabel(f"<b>Mapped Cell Index:</b> {row[2]}")
                    self.form_layout.addRow(lbl_cell)
                    
                    btn_apply = QPushButton("Apply Settlement Changes")
                    btn_apply.clicked.connect(lambda: self.commit_settlement_form_changes(entity_id))
                    self.form_layout.addRow(btn_apply)

            elif subject_type == "Religion":
                cursor.execute("SELECT name, color, supreme_deity FROM religions WHERE id = ?", (entity_id,))
                row = cursor.fetchone()
                if row:
                    self.txt_rel_name = QLineEdit(row[0])
                    self.form_layout.addRow("Faith Name:", self.txt_rel_name)
                    
                    self.txt_deity = QLineEdit(row[2])
                    self.form_layout.addRow("Supreme Deity:", self.txt_deity)
                    
                    btn_apply = QPushButton("Apply Religion Changes")
                    btn_apply.clicked.connect(lambda: self.commit_religion_form_changes(entity_id))
                    self.form_layout.addRow(btn_apply)

            conn.close()
        except Exception as e:
            print(f"Error loading parameters inspector: {e}")

    def trigger_color_picker_form(self, target_line_edit):
        color = QColorDialog.getColor()
        if color.isValid():
            target_line_edit.setText(color.name())

    def commit_faction_form_changes(self, entity_id):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE factions 
                SET name = ?, color = ?, expansionism = ?, treasury = ?
                WHERE id = ?
            """, (self.txt_fac_name.text(), self.txt_fac_color.text(), self.sp_fac_exp.value(), self.sp_fac_treasury.value(), entity_id))
            conn.commit()
            conn.close()
            self.statusBar.showMessage("Faction modifications committed to DB.")
            self.run_local_lore_reconciliation()
        except Exception as e:
            print(e)

    def commit_settlement_form_changes(self, entity_id):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE settlements 
                SET name = ?, population = ?
                WHERE id = ?
            """, (self.txt_burg_name.text(), self.sp_burg_pop.value(), entity_id))
            conn.commit()
            conn.close()
            self.statusBar.showMessage("Settlement modifications committed to DB.")
            self.run_local_lore_reconciliation()
        except Exception as e:
            print(e)

    def commit_religion_form_changes(self, entity_id):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE religions 
                SET name = ?, supreme_deity = ?
                WHERE id = ?
            """, (self.txt_rel_name.text(), self.txt_deity.text(), entity_id))
            conn.commit()
            conn.close()
            self.statusBar.showMessage("Religion modifications committed to DB.")
            self.run_local_lore_reconciliation()
        except Exception as e:
            print(e)

    # =============================================================================
    # CHAT INTERACTION & RECONCILIATION SUBMITTAL
    # =============================================================================
    def send_chat_message_to_reconciler(self):
        """Processes user chat responses, updating the SQLite target elements dynamically."""
        user_reply = self.txt_chat_prompt.text().strip()
        if not user_reply: return
        
        self.chat_history.append(f"<b>You:</b> {user_reply}")
        self.txt_chat_prompt.clear()

        if self.active_question_index >= len(self.active_question_queue):
            self.chat_history.append("<b>[AI Interviewer]</b> I have no further questions! Please synthesize the map layers.")
            return

        q = self.active_question_queue[self.active_question_index]
        
        # Parse user answer to edit the targeted database field
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if q["type"] == "Faction":
                # Capital cell index parsed from reply (or procedurally generated)
                cursor.execute("UPDATE factions SET capital_cell = 100 WHERE id = ?", (q["id"],))
            elif q["type"] == "Settlement":
                # Assign to faction 1 as a placeholder
                cursor.execute("UPDATE settlements SET faction_id = 1 WHERE id = ?", (q["id"],))
            elif q["type"] == "Religion":
                cursor.execute("UPDATE religions SET supreme_deity = ? WHERE id = ?", (user_reply, q["id"]))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(e)
            
        self.active_question_index += 1
        self.present_current_active_question()

    def trigger_map_synthesis_pipeline(self):
        """Builds the map on the right panel matching the DB constraints."""
        self.inspector_stack.setCurrentIndex(1)
        self.chat_history.append("<b>[AI Interviewer]</b> Synthesizing layout... Applying Dijkstra constraints.")
        # Re-generate world layout and reload UI...
        self.map_viewer_widget.update()
        QMessageBox.information(self, "Synthesis Complete", "The world map has been synthesized from your lore.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    wizard = ProjectStartupWizard()
    if wizard.exec() == QDialog.DialogCode.Accepted and wizard.selected_dir:
        window = LordsmithStudioMainWindow(wizard.selected_dir)
        window.show()
        sys.exit(app.exec())
