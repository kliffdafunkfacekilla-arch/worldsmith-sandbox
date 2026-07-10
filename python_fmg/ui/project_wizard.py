import os
import sqlite3
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QLabel, 
    QFileDialog, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt

class ProjectWizardDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Worldsmith Sandbox - Project Wizard")
        self.setFixedSize(400, 300)
        self.setStyleSheet("background: #111116; color: #EEEEF8;")
        self.selected_project_dir = None

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Welcome to Worldsmith Sandbox")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #04D361;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Choose how you want to start:")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        btn_new = QPushButton("Start New Project")
        btn_new.setStyleSheet("padding: 10px; background: #2A2A35; border: 1px solid #404060; border-radius: 4px;")
        btn_new.clicked.connect(self.start_new_project)
        layout.addWidget(btn_new)

        btn_load = QPushButton("Load Existing Project")
        btn_load.setStyleSheet("padding: 10px; background: #2A2A35; border: 1px solid #404060; border-radius: 4px;")
        btn_load.clicked.connect(self.load_existing_project)
        layout.addWidget(btn_load)

        btn_import = QPushButton("Import Project (Vault / Map / Text)")
        btn_import.setStyleSheet("padding: 10px; background: #2A2A35; border: 1px solid #404060; border-radius: 4px;")
        btn_import.clicked.connect(self.import_project)
        layout.addWidget(btn_import)

        layout.addStretch()

    def start_new_project(self):
        from python_fmg.ui.world_wizard import WorldCreationWizard
        wizard = WorldCreationWizard(self)
        if wizard.exec() == QDialog.DialogCode.Accepted:
            if wizard.selected_project_dir:
                self.selected_project_dir = wizard.selected_project_dir
                self.accept()

    def load_existing_project(self):
        project_dir = QFileDialog.getExistingDirectory(self, "Select Worldsmith Project Folder")
        if not project_dir:
            return

        db_path = os.path.join(project_dir, "lore_forge_world.db")
        lore_dir = os.path.join(project_dir, "lore")
        
        if not os.path.exists(db_path) and not os.path.exists(lore_dir):
            reply = QMessageBox.question(
                self, "Invalid Project", 
                "This folder does not appear to be a Worldsmith Project (missing db or lore folder).\nInitialize it as a new project anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                os.makedirs(lore_dir, exist_ok=True)
                conn = sqlite3.connect(db_path)
                conn.close()
                self.selected_project_dir = project_dir
                self.accept()
            return
            
        self.selected_project_dir = project_dir
        self.accept()

    def import_project(self):
        QMessageBox.information(
            self, "Import Project", 
            "To import an Obsidian Vault or external files, please first create a New Project or load an empty one, then use the Import buttons in the main application."
        )
        self.start_new_project()