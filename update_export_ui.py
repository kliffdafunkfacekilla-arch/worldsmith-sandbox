import os

filepath = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add import
old_import = "from python_fmg.core.azgaar_engine import AzgaarEngine, CosmosEngine"
new_import = "from python_fmg.core.azgaar_engine import AzgaarEngine, CosmosEngine\nfrom python_fmg.core.export_engine import WorldsmithExportEngine"

if old_import in content:
    content = content.replace(old_import, new_import)
else:
    print("Could not find import block.")

# 2. Add self.export_engine and action to menu
old_menu = """        self.map_engine = AzgaarEngine()

        # Build Export Menu
        file_menu = self.menuBar().addMenu("File")
        
        action_export_geojson = file_menu.addAction("Export GeoJSON Framework")
        action_export_geojson.triggered.connect(self.action_export_geojson)
        
        action_export_wiki = file_menu.addAction("Export Static HTML Wiki")
        action_export_wiki.triggered.connect(self.action_export_wiki)"""

new_menu = """        self.map_engine = AzgaarEngine()
        self.export_engine = WorldsmithExportEngine(self)

        # Build Export Menu
        file_menu = self.menuBar().addMenu("File")
        
        action_export_geojson = file_menu.addAction("Export GeoJSON Framework")
        action_export_geojson.triggered.connect(self.action_export_geojson)
        
        action_export_wiki = file_menu.addAction("Export Static HTML Wiki")
        action_export_wiki.triggered.connect(self.action_export_wiki)
        
        action_export_sim = file_menu.addAction("Export Simulation Seed")
        action_export_sim.triggered.connect(self.action_export_simulation)"""

if old_menu in content:
    content = content.replace(old_menu, new_menu)
else:
    print("Could not find menu block.")

# 3. Add method definition
old_method = """    def action_export_wiki(self):
        pass"""

new_method = """    def action_export_wiki(self):
        pass
        
    def action_export_simulation(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save World Seed", "world_seed.json", "JSON Files (*.json)")
        if file_path:
            self.export_engine.export_simulation_seed(file_path, db_path=self.db_path)
            QMessageBox.information(self, "Export Complete", f"Simulation seed successfully exported to {file_path}")"""

if old_method in content:
    content = content.replace(old_method, new_method)
else:
    print("Could not find action_export_wiki method to append to. Will just append it at the end of the class.")
    # Append the method to the end of the class. Let's find handle_ai_response which is at the very end
    old_method_fallback = """    def handle_ai_response(self, text):
        self.ai_prompt_history.append(
            f'<div style="text-align: left; margin: 2px 30px 6px 4px;">'
            f'<span style="background-color: #29293a; color: #EEEEF8; padding: 4px 8px; border-radius: 6px; display: inline-block;">'
            f'<span style="color: #04D361; font-weight: bold;">AI:</span> {text}</span></div>'
        )"""
        
    new_method_fallback = """    def handle_ai_response(self, text):
        self.ai_prompt_history.append(
            f'<div style="text-align: left; margin: 2px 30px 6px 4px;">'
            f'<span style="background-color: #29293a; color: #EEEEF8; padding: 4px 8px; border-radius: 6px; display: inline-block;">'
            f'<span style="color: #04D361; font-weight: bold;">AI:</span> {text}</span></div>'
        )

    def action_export_simulation(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save World Seed", "world_seed.json", "JSON Files (*.json)")
        if file_path:
            self.export_engine.export_simulation_seed(file_path, db_path=self.db_path)
            QMessageBox.information(self, "Export Complete", f"Simulation seed successfully exported to {file_path}")"""
    if old_method_fallback in content:
        content = content.replace(old_method_fallback, new_method_fallback)
    else:
        print("COULD NOT APPEND METHOD!")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Finished update script for main.py")
