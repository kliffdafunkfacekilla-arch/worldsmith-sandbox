import os
import sqlite3
import json
from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QComboBox, QTextEdit, QFileDialog, QPushButton, 
    QMessageBox, QCheckBox, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt
from python_fmg.core.template_manager import TemplateManager

class FoundationPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("World Foundation")
        self.setSubTitle("Set the name, location, and genre of your new world.")

        layout = QVBoxLayout(self)

        # Name
        layout.addWidget(QLabel("Project/World Name:"))
        self.name_input = QLineEdit()
        self.registerField("project_name*", self.name_input)
        layout.addWidget(self.name_input)

        # Directory
        layout.addWidget(QLabel("Project Location:"))
        h_layout = QHBoxLayout()
        self.dir_input = QLineEdit()
        self.dir_input.setReadOnly(True)
        # Default to Documents folder
        default_dir = os.path.join(os.path.expanduser("~"), "Documents", "Worldsmith")
        if not os.path.exists(default_dir):
            try:
                os.makedirs(default_dir)
            except:
                default_dir = os.path.expanduser("~")
        self.dir_input.setText(default_dir)
        self.registerField("project_dir", self.dir_input)
        h_layout.addWidget(self.dir_input)
        
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self.browse_dir)
        h_layout.addWidget(btn_browse)
        layout.addLayout(h_layout)

        # Genre
        layout.addWidget(QLabel("Genre:"))
        self.genre_combo = QComboBox()
        self.genre_combo.addItems(["Fantasy", "Sci-Fi", "Cyberpunk", "Post-Apocalyptic", "Historical Fiction", "Modern Day", "Horror"])
        self.registerField("genre", self.genre_combo, "currentText")
        layout.addWidget(self.genre_combo)

        # Tone
        layout.addWidget(QLabel("Tone:"))
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(["Grimdark", "Heroic", "Realistic", "Noblebright", "Comedic", "Surreal"])
        self.registerField("tone", self.tone_combo, "currentText")
        layout.addWidget(self.tone_combo)

    def browse_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Base Directory")
        if directory:
            self.dir_input.setText(directory)


class CosmologyPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Cosmology & Geography")
        self.setSubTitle("Define the universe and terrain style of your world.")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Cosmology Overview (e.g., A flat world on a turtle, A binary star system):"))
        self.cosmology_input = QTextEdit()
        self.cosmology_input.setPlaceholderText("Describe the physical laws, stars, gods, or creation myth...")
        self.registerField("cosmology", self.cosmology_input, "plainText")
        layout.addWidget(self.cosmology_input)

        layout.addWidget(QLabel("Geography Style:"))
        self.geo_combo = QComboBox()
        self.geo_combo.addItems(["Pangea (Single Supercontinent)", "Archipelagos (Many islands)", "Two Continents", "Desert World", "Water World", "Subterranean"])
        self.registerField("geography", self.geo_combo, "currentText")
        layout.addWidget(self.geo_combo)


class TemplatesPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Subject Templates")
        self.setSubTitle("Select the baseline templates you want to include in this project.")

        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.v_layout = QVBoxLayout(container)

        self.default_templates = {
            "History-Timeline": ["Era", "Major Events", "Key Figures"],
            "Cosmology": ["Origin Myth", "Physical Laws", "Planes of Existence"],
            "Magic-Powers": ["Rules", "Sources", "Limitations"],
            "Tech": ["Tech Era", "Core Inventions", "Resource Dependencies"],
            "Cultures": ["Traditions", "Values", "Taboos"],
            "Kingdoms-Empires-Countries": ["Government", "Demographics", "Territory"],
            "Factions-Organizations": ["Purpose", "Hierarchy", "Influence"],
            "Species": ["Biology", "Lifespan", "Habitats"],
            "Locations": ["Climate", "Geography", "Points of Interest"],
            "People": ["Appearance", "Personality", "Background"],
            "Religions": ["Deities", "Dogma", "Practices"],
            "Items-Objects": ["Appearance", "Function", "History"],
            "Flora": ["Environment", "Uses", "Hazards"],
            "Fauna": ["Diet", "Behavior", "Abilities"],
            "Economy": ["Currency", "Major Exports", "Wealth Distribution"],
            "Ecology": ["Biomes", "Food Chains", "Climate Trends"],
            "Meta": ["Themes", "Tropes", "Inspirations"]
        }

        self.checkboxes = {}
        for cat in self.default_templates.keys():
            chk = QCheckBox(cat)
            chk.setChecked(True)
            self.checkboxes[cat] = chk
            self.v_layout.addWidget(chk)

        self.v_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def get_selected_templates(self):
        selected = {}
        for cat, chk in self.checkboxes.items():
            if chk.isChecked():
                selected[cat] = self.default_templates[cat]
        return selected


class WorldCreationWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New World")
        self.setFixedSize(600, 500)
        self.setStyleSheet("background: #111116; color: #EEEEF8;")
        
        self.selected_project_dir = None

        self.page1 = FoundationPage()
        self.page2 = CosmologyPage()
        self.page3 = TemplatesPage()

        self.addPage(self.page1)
        self.addPage(self.page2)
        self.addPage(self.page3)

    def accept(self):
        project_name = self.field("project_name")
        base_dir = self.field("project_dir")
        genre = self.field("genre")
        tone = self.field("tone")
        cosmology = self.field("cosmology")
        geography = self.field("geography")
        selected_templates = self.page3.get_selected_templates()

        project_dir = os.path.join(base_dir, project_name.strip())
        
        try:
            # 1. Create Directories
            os.makedirs(project_dir, exist_ok=True)
            lore_dir = os.path.join(project_dir, "lore")
            os.makedirs(lore_dir, exist_ok=True)
            
            # Generate subfolders for each template
            for cat in self.page3.default_templates.keys():
                os.makedirs(os.path.join(lore_dir, cat), exist_ok=True)
            
            # 2. Setup Database
            db_path = os.path.join(project_dir, "lore_forge_world.db")
            conn = sqlite3.connect(db_path)
            # Create required tables for templates to work
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS world_templates (
                    category TEXT PRIMARY KEY,
                    fields_json TEXT NOT NULL
                )
            """)
            
            for cat, fields in selected_templates.items():
                cursor.execute("""
                    INSERT OR IGNORE INTO world_templates (category, fields_json)
                    VALUES (?, ?)
                """, (cat, json.dumps(fields)))
                
            conn.commit()
            conn.close()

            # 3. Create World Baseline Document
            baseline_path = os.path.join(lore_dir, "[World Baseline].md")
            baseline_content = f"""# {project_name} - World Baseline

## Foundation
**Genre**: {genre}
**Tone**: {tone}

## Geography
**Primary Style**: {geography}

## Cosmology
{cosmology}
"""
            with open(baseline_path, "w", encoding="utf-8") as f:
                f.write(baseline_content)

            self.selected_project_dir = project_dir
            super().accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Creation Error", f"Failed to create world: {e}")
            # Don't call super().accept() so wizard stays open
