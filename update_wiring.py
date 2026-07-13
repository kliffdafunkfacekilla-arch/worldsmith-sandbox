import os

filepath = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Inject Menu Action
old_menu = """        # Build Export Menu
        file_menu = self.menuBar().addMenu("File")
        
        action_export_geojson = file_menu.addAction("Export GeoJSON Framework")"""

new_menu = """        # Build Export Menu
        file_menu = self.menuBar().addMenu("File")
        
        action_generate_map = file_menu.addAction("🎲 Generate Procedural World Map")
        action_generate_map.triggered.connect(self.action_generate_procedural_world)
        
        file_menu.addSeparator()
        
        action_export_geojson = file_menu.addAction("Export GeoJSON Framework")"""

if old_menu in content:
    content = content.replace(old_menu, new_menu)

# 2. Modify on_ingestion_complete to trigger audit
old_ingest = """    def on_ingestion_complete(self, is_online):
        self.progress_dialog.setValue(self.progress_dialog.maximum())
        if is_online:
            QMessageBox.information(self, "Success", "Lore successfully ingested and synchronized with SQLite database!")
        else:
            QMessageBox.warning(self, "Offline Mode", "Lore was saved as plain text, but AI Entity Extraction failed! No Ollama instance was found on port 11434 and no Gemini API key was provided.")
        self.w_factions.refresh_grid()
        self.w_provinces.refresh_grid()
        # Trigger map canvas re-render since new cities might have spawned
        self.map_viewer_canvas.update()"""

new_ingest = """    def on_ingestion_complete(self, is_online):
        self.progress_dialog.setValue(self.progress_dialog.maximum())
        if is_online:
            QMessageBox.information(self, "Success", "Lore successfully ingested and synchronized with SQLite database!")
        else:
            QMessageBox.warning(self, "Offline Mode", "Lore was saved as plain text, but AI Entity Extraction failed! No Ollama instance was found on port 11434 and no Gemini API key was provided.")
        self.w_factions.refresh_grid()
        self.w_provinces.refresh_grid()
        # Trigger map canvas re-render since new cities might have spawned
        self.map_viewer_canvas.update()
        
        # Switch to chat tab and trigger proactive AI audit
        self.left_tabs.setCurrentWidget(self.tab_chat)
        self.trigger_lore_audit()"""

if old_ingest in content:
    content = content.replace(old_ingest, new_ingest)

# 3. Add trigger_lore_audit and action_generate_procedural_world
old_handle_ai = """    def handle_ai_response(self, text):
        self.ai_prompt_history.append(
            f'<div style="text-align: left; margin: 2px 30px 6px 4px;">'
            f'<span style="background-color: #29293a; color: #EEEEF8; padding: 4px 8px; border-radius: 6px; display: inline-block;">'
            f'<span style="color: #04D361; font-weight: bold;">AI:</span> {text}</span></div>'
        )"""

new_handle_ai = """    def trigger_lore_audit(self):
        self.handle_ai_response("Processing worldstate... Analyzing database rules, actors, and diplomatic pressures...")
        try:
            import json
            import sqlite3
            conn = sqlite3.connect(self.db_path, timeout=15.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()

            cursor.execute("SELECT name, gov_type FROM factions")
            factions = cursor.fetchall()
            
            # Use a try/except for actors in case the DB hasn't been wiped yet in older test setups
            try:
                cursor.execute("SELECT name, is_alive, role FROM actors")
                actors = cursor.fetchall()
            except sqlite3.OperationalError:
                actors = []

            cursor.execute("SELECT name, population FROM settlements")
            settlements = cursor.fetchall()
            conn.close()

            db_summary = {
                "factions": [f"{f[0]} ({f[1]})" for f in factions],
                "actors": [f"{a[0]} ({a[2]}) - {'Alive' if a[1] else 'Dead'}" for a in actors],
                "settlements": [f"{s[0]} (Pop: {s[1]})" for s in settlements]
            }
            summary_str = json.dumps(db_summary, indent=2)
            
            from python_fmg.core.ai_worker import AILoreDriverWorker
            self.driver_worker = AILoreDriverWorker(system_state=summary_str, parent=self)
            self.driver_worker.query_resolved.connect(self.handle_ai_response)
            self.driver_worker.start()
        except Exception as e:
            self.handle_ai_response(f"Audit failed: {e}")

    def action_generate_procedural_world(self):
        try:
            self.statusBar().showMessage("Generating Procedural World Map...")
            self.map_engine.generate_voronoi_mesh(1000)
            self.map_engine.run_heightmap_pipeline()
            if hasattr(self.map_engine, 'run_biomes_climate'):
                self.map_engine.run_biomes_climate()
            if hasattr(self.map_engine, 'run_hydrology_rivers'):
                self.map_engine.run_hydrology_rivers()
            if hasattr(self.map_engine, 'run_states_expansion'):
                self.map_engine.run_states_expansion()
            self.map_engine.sink_generated_world_to_db(self.db_path)
            
            self.btn_toggle_map.setChecked(True)
            self.toggle_map_view(True)
            self.map_viewer_canvas.update()
            
            self.statusBar().showMessage("World Map Generation Complete!")
            QMessageBox.information(self, "Success", "Procedural World Map successfully generated from the current database state!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate map: {e}")

    def handle_ai_response(self, text):
        self.ai_prompt_history.append(
            f'<div style="text-align: left; margin: 2px 30px 6px 4px;">'
            f'<span style="background-color: #29293a; color: #EEEEF8; padding: 4px 8px; border-radius: 6px; display: inline-block;">'
            f'<span style="color: #04D361; font-weight: bold;">AI:</span> {text}</span></div>'
        )"""

if old_handle_ai in content:
    content = content.replace(old_handle_ai, new_handle_ai)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Wiring complete for map generation and lore audit.")
