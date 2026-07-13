import os

filepath = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """class ProjectStartupWizard(QDialog):
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
            self.accept()"""

new_block = """class ProjectStartupWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_dir = None
        self.import_notes = False
        self.setWindowTitle("Lordsmith Studio Startup")
        self.resize(460, 280)
        self.setStyleSheet("background-color: #111116; color: #EEEEF8; font-family: Arial; QPushButton { padding: 8px; margin: 4px; }")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>🌌 Welcome to Lordsmith Studio</h2>"))
        
        btn_open = QPushButton("📂 Open Existing Project")
        btn_open.clicked.connect(self.action_open_project)
        layout.addWidget(btn_open)

        btn_import = QPushButton("📥 Start New by Importing Notes")
        btn_import.clicked.connect(self.action_import_new)
        layout.addWidget(btn_import)
        
        btn_new = QPushButton("📄 Start Blank Project")
        btn_new.clicked.connect(self.action_new_project)
        layout.addWidget(btn_new)

    def action_open_project(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Existing Project Directory")
        if dir_path:
            self.selected_dir = dir_path
            self.import_notes = False
            self.accept()
            
    def action_import_new(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory for New Project")
        if dir_path:
            self.selected_dir = dir_path
            self.import_notes = True
            self.accept()

    def action_new_project(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory for New Project")
        if dir_path:
            self.selected_dir = dir_path
            self.import_notes = False
            self.accept()"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('ProjectStartupWizard Updated')
else:
    print('Could not find ProjectStartupWizard block')


old_main = """if __name__ == "__main__":
    app = QApplication(sys.argv)
    wizard = ProjectStartupWizard()
    if wizard.exec() == QDialog.DialogCode.Accepted and wizard.selected_dir:
        window = LordsmithStudioMainWindow(wizard.selected_dir)
        window.show()
        sys.exit(app.exec())"""

new_main = """if __name__ == "__main__":
    app = QApplication(sys.argv)
    wizard = ProjectStartupWizard()
    if wizard.exec() == QDialog.DialogCode.Accepted and wizard.selected_dir:
        window = LordsmithStudioMainWindow(wizard.selected_dir)
        window.show()
        if wizard.import_notes:
            # use QTimer to trigger import dialogue shortly after UI shows
            QTimer.singleShot(500, window.action_import_lore)
        sys.exit(app.exec())"""

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

if old_main in content:
    content = content.replace(old_main, new_main)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Main Block Updated')
else:
    print('Could not find Main block')
