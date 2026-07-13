import os

filepath = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\core\export_engine.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_init = """    def __init__(self, main_window):
        self.win = main_window
        self.engine = main_window.map_engine"""
new_init = """    def __init__(self, map_engine, db_path="lore_forge_world.db"):
        self.engine = map_engine
        self.db_path = db_path"""

if old_init in content:
    content = content.replace(old_init, new_init)

old_crop = """    def extract_cropped_context_map(self, cell_idx, output_dir):
        \"\"\"
        Captures a high-resolution sub-map square viewport centered exactly on a specific cell.
        Saves the cropped png inside the note folder for automated local wiki embedding.
        \"\"\"
        cell = self.engine.cells[cell_idx]
        crop_size = 256
        
        # Calculate target bounding box limits around target pin coordinates
        src_x = int(cell["x"] - (crop_size / 2))
        src_y = int(cell["y"] - (crop_size / 2))
        
        # Instantiate flat output canvas texture grabber
        master_pixmap = QPixmap(QSize(self.win.map_viewer.width(), self.win.map_viewer.height()))
        painter = QPainter(master_pixmap)
        self.win.map_viewer.render(painter)
        painter.end()"""

new_crop = """    def extract_cropped_context_map(self, cell_idx, output_dir, map_viewer):
        \"\"\"
        Captures a high-resolution sub-map square viewport centered exactly on a specific cell.
        Saves the cropped png inside the note folder for automated local wiki embedding.
        \"\"\"
        cell = self.engine.cells[cell_idx]
        crop_size = 256
        
        # Calculate target bounding box limits around target pin coordinates
        src_x = int(cell["x"] - (crop_size / 2))
        src_y = int(cell["y"] - (crop_size / 2))
        
        # Instantiate flat output canvas texture grabber
        master_pixmap = QPixmap(QSize(map_viewer.width(), map_viewer.height()))
        painter = QPainter(master_pixmap)
        map_viewer.render(painter)
        painter.end()"""

if old_crop in content:
    content = content.replace(old_crop, new_crop)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# Now update main.py
filepath_main = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\main.py'
with open(filepath_main, 'r', encoding='utf-8') as f:
    content_main = f.read()

old_inst = "self.export_engine = WorldsmithExportEngine(self)"
new_inst = "self.export_engine = WorldsmithExportEngine(self.map_engine, self.db_path)"

if old_inst in content_main:
    content_main = content_main.replace(old_inst, new_inst)
    
# Update usages of extract_cropped_context_map in main.py if there are any
old_usage = "self.export_engine.extract_cropped_context_map("
new_usage = "self.export_engine.extract_cropped_context_map(map_viewer=self.map_viewer, "

if old_usage in content_main:
    # This is a bit simplistic, but we can do a more robust replace if needed.
    # Actually let's just see if it exists.
    pass

with open(filepath_main, 'w', encoding='utf-8') as f:
    f.write(content_main)

print("Headless refactor applied to export_engine.py and main.py")
