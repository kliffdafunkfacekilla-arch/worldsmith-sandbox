import os
import sys
import sqlite3
import json
import urllib.request
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QLineEdit, QPushButton, QStatusBar, QMessageBox, QComboBox, QSlider
)
from PyQt6.QtCore import Qt

# Add project root directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from python_fmg.core.ai_worker import OllamaPromptWorker
from python_fmg.renderers.map_viewer import MapViewerWidget
from python_fmg.renderers.notebook_editor import MarkdownNotebookEditor
from python_fmg.core.azgaar_engine import AzgaarEngine
from python_fmg.core.wiki_compiler import WikiCompiler
from python_fmg.renderers.celestial_widget import CelestialPreviewWidget

class WorldsmithMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Worldsmith Sandbox - Independent Worldbuilder")
        self.resize(1400, 950)
        
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lore_forge_world.db"))
        self.ai_worker = None
        self.selected_cell_idx = None
        
        # Calendar settings
        self.custom_year_length = 420  
        self.custom_seasons = ["Sowing-Time", "High-Sun", "Gold-Leaf", "Deep-Frost"]
        
        # Initialize full Azgaar simulation logic including all parameters and layers
        self.map_engine = AzgaarEngine()
        self.map_engine.run_heightmap_pipeline()
        self.map_engine.run_hydrology_rivers()
        self.map_engine.run_biomes_climate()
        self.map_engine.run_cultures_generation()
        self.map_engine.run_states_expansion()
        self.map_engine.run_provinces_generation()
        self.map_engine.run_religions_generation()
        self.map_engine.run_burgs_generation()
        self.map_engine.run_roads_pathfinding()
        self.map_engine.run_military_generator()
        self.map_engine.run_production_goods()

        # Modern Dark-Mode Stylesheet
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #121214;
                color: #E1E1E6;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #29292E;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #04D361;
            }
            QPushButton, QComboBox {
                background-color: #202024;
                border: 1px solid #29292E;
                color: #E1E1E6;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover, QComboBox:hover {
                background-color: #29292E;
                border-color: #04D361;
            }
            QLineEdit, QTextEdit, QListWidget {
                background-color: #1c1c21;
                border: 1px solid #29292E;
                border-radius: 4px;
                padding: 6px;
                color: #E1E1E6;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #04D361;
            }
        """)

        # Main Splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.main_splitter)

        # 1. Map Panel
        self.map_container = QWidget()
        map_layout = QVBoxLayout(self.map_container)
        map_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add Toolbar for Map Selection Layers and Magic Brush
        map_toolbar = QHBoxLayout()
        self.cb_layer = QComboBox()
        self.cb_layer.addItems(["Elevation", "Biomes", "Political States", "Magic Layer"])
        self.cb_layer.currentTextChanged.connect(self.change_map_layer)
        
        self.cb_magic_brush = QComboBox()
        self.cb_magic_brush.addItems(["Wild Magic", "Abyssal Corruption", "Ley Line Node", "Aether Storm", "None"])
        self.cb_magic_brush.currentTextChanged.connect(self.change_magic_brush)
        self.cb_magic_brush.setVisible(False)  # Only visible when Magic Layer is active
        
        map_toolbar.addWidget(QLabel("<b>Render Layer:</b>"))
        map_toolbar.addWidget(self.cb_layer)
        self.lbl_magic_brush = QLabel("<b>Magic Type Brush:</b>")
        self.lbl_magic_brush.setVisible(False)
        map_toolbar.addWidget(self.lbl_magic_brush)
        map_toolbar.addWidget(self.cb_magic_brush)
        map_toolbar.addStretch()
        
        self.map_viewer = MapViewerWidget(self)
        self.map_viewer.cell_hovered.connect(self.handle_cell_hovered)
        self.map_viewer.cell_clicked.connect(self.handle_cell_painted)
        self.load_map_data_to_viewer()
        
        map_layout.addLayout(map_toolbar)
        map_layout.addWidget(self.map_viewer)
        self.main_splitter.addWidget(self.map_container)

        # 2. Notebook Panel
        self.note_container = QWidget()
        note_layout = QVBoxLayout(self.note_container)
        
        self.note_title_input = QLineEdit()
        self.note_title_input.setPlaceholderText("Note Title (e.g. Faction, Settlement, Region name)")
        self.note_title_input.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        self.note_editor = MarkdownNotebookEditor(self)
        self.note_editor.tag_detected.connect(self.handle_tag_found)
        self.note_editor.link_clicked.connect(self.handle_link_clicked)
        
        self.note_action_layout = QHBoxLayout()
        self.btn_save_note = QPushButton("💾 Save Note")
        self.btn_save_note.clicked.connect(self.save_current_note)
        self.btn_delete_note = QPushButton("🗑️ Delete")
        self.btn_compile_wiki = QPushButton("🌐 Compile Wiki")
        self.btn_compile_wiki.clicked.connect(self.compile_static_wiki)
        self.btn_bind_map = QPushButton("📍 Bind to Cell")
        self.btn_bind_map.clicked.connect(self.bind_note_to_map_cell)
        
        self.note_action_layout.addWidget(self.btn_save_note)
        self.note_action_layout.addWidget(self.btn_bind_map)
        self.note_action_layout.addWidget(self.btn_delete_note)
        self.note_action_layout.addWidget(self.btn_compile_wiki)
        
        note_layout.addWidget(QLabel("<b>Obsidian-Style Notebook</b>"))
        note_layout.addWidget(self.note_title_input)
        note_layout.addWidget(self.note_editor)
        note_layout.addLayout(self.note_action_layout)
        self.main_splitter.addWidget(self.note_container)

        # 3. Prompt-Driven AI Assistant Panel
        self.ai_container = QWidget()
        ai_layout = QVBoxLayout(self.ai_container)
        
        self.ai_prompt_history = QTextEdit()
        self.ai_prompt_history.setReadOnly(True)
        self.ai_prompt_history.setPlaceholderText("The AI will ask questions and guide your worldbuilding process...")
        
        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("Answer prompts, ask to generate states, etc...")
        self.ai_input.returnPressed.connect(self.send_ai_prompt)
        
        self.btn_send_prompt = QPushButton("⚡ Send Response")
        self.btn_send_prompt.clicked.connect(self.send_ai_prompt)
        
        # Add Timeline Slider and Celestial Moon Previewer
        self.timeline_layout = QVBoxLayout()
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setRange(1, self.custom_year_length)
        self.timeline_slider.setValue(1)
        self.timeline_slider.valueChanged.connect(self.handle_timeline_changed)
        
        self.lbl_timeline = QLabel(f"<b>Calendar Timeline (Day 1 / {self.custom_seasons[0]})</b>")
        self.celestial_widget = CelestialPreviewWidget(self)
        
        self.timeline_layout.addWidget(self.lbl_timeline)
        self.timeline_layout.addWidget(self.timeline_slider)
        self.timeline_layout.addWidget(self.celestial_widget)
        
        ai_layout.addWidget(QLabel("<b>Co-Author Assistant</b>"))
        ai_layout.addWidget(self.ai_prompt_history)
        ai_layout.addWidget(self.ai_input)
        ai_layout.addWidget(self.btn_send_prompt)
        ai_layout.addLayout(self.timeline_layout)
        
        self.main_splitter.addWidget(self.ai_container)

        # Set sizes (40% Map, 35% Note, 25% AI)
        self.main_splitter.setSizes([560, 490, 350])

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Worldsmith ready.")

        # Setup databases
        self.setup_markers_db()
        self.setup_magic_db()

        # Welcome Prompt
        self.trigger_welcome_prompt()

    def setup_markers_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS note_map_bindings (
                    note_id INTEGER,
                    cell_idx INTEGER UNIQUE,
                    FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
            conn.close()
        except:
            pass

    def setup_magic_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
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

    def change_magic_brush(self, brush_name):
        self.map_viewer.active_paint_magic = brush_name

    def handle_cell_painted(self, idx):
        # Save painted magic type directly to SQLite
        try:
            conn = sqlite3.connect(self.db_path)
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

    def handle_timeline_changed(self, day_val):
        num_seasons = len(self.custom_seasons)
        season_duration = self.custom_year_length / num_seasons
        season_idx = min(int((day_val - 1) / season_duration), num_seasons - 1)
        season = self.custom_seasons[season_idx]
            
        self.lbl_timeline.setText(f"<b>Calendar Timeline (Day {day_val} / {season})</b>")
        self.celestial_widget.set_day(day_val)

    def handle_cell_hovered(self, idx, elev, biome, state):
        self.selected_cell_idx = idx
        
        bound_note_title = "None"
        try:
            conn = sqlite3.connect(self.db_path)
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
                
        cell = self.map_engine.cells[idx]
        province = f"Province {cell['province']}" if cell["province"] > 0 else "None"
        culture = f"Culture {cell['culture']}" if cell["culture"] > 0 else "None"
        religion = f"Religion {cell['religion']}" if cell["religion"] > 0 else "None"
        
        self.statusBar.showMessage(
            f"Cell ID: {idx} | Bound Note: {bound_note_title} | State: {state} | "
            f"Prov: {province} | Cult: {culture} | Rel: {religion} | Troops: {troops}"
        )

    def bind_note_to_map_cell(self):
        title = self.note_title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "No Note", "Save or open a note first before binding it to a map cell.")
            return
        if self.selected_cell_idx is None:
            QMessageBox.warning(self, "No Cell Hovered", "Hover over a map cell coordinate before binding.")
            return

        try:
            conn = sqlite3.connect(self.db_path)
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
            self.statusBar.showMessage(f"Successfully bound note '{title}' to Cell ID: {self.selected_cell_idx}.")
        except Exception as e:
            QMessageBox.critical(self, "Binding Error", f"Failed to bind note: {e}")

    def load_map_data_to_viewer(self):
        # Read saved magic data first to fill viewer cache
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT cell_idx, magic_type FROM magic_layers")
            for cell_idx, m_type in cursor.fetchall():
                # Recover key (q, r)
                for cell in self.map_viewer.grid_cells:
                    if cell["idx"] == cell_idx:
                        self.map_viewer.magic_data[(cell["q"], cell["r"])] = m_type
            conn.close()
        except:
            pass

        for cell in self.map_engine.cells:
            q = cell["i"] * 100
            r = cell["i"] * 50 - cell["i"]
            self.map_viewer.elevation_data[(q, r)] = cell["h"]
            self.map_viewer.biomes_data[(q, r)] = cell["biome"]
            
            if cell["state"] > 0:
                color_hex = "#7f1d1d"
                for st in self.map_engine.states:
                    if st["id"] == cell["state"]:
                        color_hex = st["color"]
                self.map_viewer.factions_data[(q, r)] = color_hex
            else:
                self.map_viewer.factions_data[(q, r)] = "#18181b"
        self.map_viewer.update()

    def trigger_welcome_prompt(self):
        welcome_text = (
            "<b>[System] Welcome to Worldsmith Sandbox!</b><br><br>"
            "I am your co-author AI. Let's start at the beginning. "
            "What is the name of the fantasy world we are building today? "
            "Provide a name, and briefly describe what kind of climate or geography it has."
        )
        self.ai_prompt_history.append(welcome_text)

    def change_map_layer(self, layer_name):
        self.map_viewer.layer_mode = layer_name
        
        # Show/Hide magic brush control depending on layer selection
        is_magic = (layer_name == "Magic Layer")
        self.lbl_magic_brush.setVisible(is_magic)
        self.cb_magic_brush.setVisible(is_magic)
        
        self.map_viewer.update()

    def handle_tag_found(self, tag_name):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
            conn.commit()
            conn.close()
        except:
            pass

    def handle_link_clicked(self, link_title):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM notes WHERE title=?", (link_title,))
            row = cursor.fetchone()
            conn.close()
            
            self.note_title_input.setText(link_title)
            if row:
                self.note_editor.setPlainText(row[0])
                self.statusBar.showMessage(f"Loaded note '{link_title}'.")
            else:
                self.note_editor.setPlainText("")
                self.statusBar.showMessage(f"Note '{link_title}' not found. Start typing to create it.")
        except Exception as e:
            self.statusBar.showMessage(f"Error opening link: {e}")

    def send_ai_prompt(self):
        user_text = self.ai_input.text().strip()
        if not user_text:
            return
        
        self.ai_prompt_history.append(f"<br><b>You:</b> {user_text}")
        self.ai_input.clear()
        
        self.statusBar.showMessage("AI is thinking...")
        self.btn_send_prompt.setEnabled(False)

        # Start Async Worker Thread with dynamic db scan
        self.ai_worker = OllamaPromptWorker(user_text, db_path=self.db_path)
        self.ai_worker.response_received.connect(self.handle_ai_response)
        self.ai_worker.error_occurred.connect(self.handle_ai_error)
        self.ai_worker.start()

    def handle_ai_response(self, text):
        self.ai_prompt_history.append(f"<br><b>AI Assistant:</b> {text}<br>")
        self.statusBar.showMessage("Response received.")
        self.btn_send_prompt.setEnabled(True)

    def handle_ai_error(self, err_msg):
        self.ai_prompt_history.append(f"<br><font color='red'><b>[Error]:</b> Failed to communicate with local Ollama server ({err_msg}). Ensure Ollama is running (`ollama serve`).</font><br>")
        self.statusBar.showMessage("AI communication error.")
        self.btn_send_prompt.setEnabled(True)

    def save_current_note(self):
        title = self.note_title_input.text().strip()
        content = self.note_editor.toPlainText().strip()
        
        if not title:
            QMessageBox.warning(self, "Missing Title", "Please provide a title for the note.")
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notes (title, content, updated_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(title) DO UPDATE SET content=excluded.content, updated_at=CURRENT_TIMESTAMP
            """, (title, content))
            conn.commit()
            conn.close()
            self.statusBar.showMessage(f"Note '{title}' saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save note: {e}")

    def compile_static_wiki(self):
        compiler = WikiCompiler(self.db_path)
        success, msg = compiler.compile_wiki()
        if success:
            QMessageBox.information(self, "Wiki Compiled", msg)
        else:
            QMessageBox.critical(self, "Compilation Error", f"Failed to compile wiki: {msg}")

def main():
    app = QApplication(sys.argv)
    window = WorldsmithMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
