import math
import random
import sqlite3
import json
from PyQt6.QtGui import QImage, qRed

# =============================================================================
# COSMOS COSMOLOGY REGULATOR
# =============================================================================
class CosmosEngine:
    """Manages global celestial parameters, year day-cycles, and active orbital lengths."""
    def __init__(self, year_length=420, seasons=None):
        self.year_length = year_length
        self.seasons = seasons if seasons else ["Winter", "Spring", "Summer", "Autumn"]


# =============================================================================
# THE SPATIAL GENERATION ENGINE
# =============================================================================
class AzgaarEngine:
    """
    Simulates coordinate meshes, rainfall, temperatures, biomes, and territorial
    Dijkstra cost-field boundaries, matching both land and underwater domains.
    """
    def __init__(self):
        self.cells = []
        self.states = []
        self.burgs = []
        self.cultures = []
        self.religions = []
        self.width = 1000  # Added for image heightmap logic
        self.height = 1000 # Added for image heightmap logic
        self.size = 1000  # Number of grid points

    def generate_voronoi_mesh(self, num_cells=1000):
        """
        Generates an organic, Poisson-jittered coordinate grid.
        Avoids C-based Scipy/Numpy dependencies to ensure guaranteed pure-Python execution.
        """
        self.size = num_cells
        self.cells = []
        # Generate jittered coordinate array (symmetrical relaxation approximation)
        cols_rows = int(math.sqrt(self.size))
        spacing = 1000.0 / cols_rows

        cell_id = 0
        for r in range(cols_rows):
            for c in range(cols_rows):
                # Add random organic jitter to break uniform grid lines
                jx = random.uniform(-spacing * 0.4, spacing * 0.4)
                jy = random.uniform(-spacing * 0.4, spacing * 0.4)
                
                cx = (c * spacing) + (spacing / 2.0) + jx
                cy = (r * spacing) + (spacing / 2.0) + jy
                
                # Symmetrical safety bounds
                cx = max(10, min(cx, 990))
                cy = max(10, min(cy, 990))

                self.cells.append({
                    "i": cell_id,
                    "centroid_x": cx,
                    "centroid_y": cy,
                    "h": 20,          # Default elevation coastline threshold
                    "temp": 15,       # Baseline celsius
                    "prec": 10,       # Baseline moisture/nutrients
                    "biome": "Marine",
                    "state": 0,       # Unclaimed neutral territory
                    "province": 0,
                    "culture": 0,
                    "religion": 0,
                    "river_id": 0,
                    "flow_accumulation": 0.0,
                    "downhill_neighbor": -1,
                    "neighbors": []
                })
                cell_id += 1

        # Build pure-Python Delaunay adjacency graphs using k-nearest centroids
        for cell in self.cells:
            cx, cy = cell["centroid_x"], cell["centroid_y"]
            distances = []
            for target in self.cells:
                if target["i"] == cell["i"]:
                    continue
                tx, ty = target["centroid_x"], target["centroid_y"]
                dist = math.sqrt((cx - tx)**2 + (cy - ty)**2)
                distances.append((dist, target["i"]))
            
            # Sort and pick the 6 nearest cells as natural Voronoi neighbors
            distances.sort()
            cell["neighbors"] = [idx for _, idx in distances[:6]]

    def run_heightmap_pipeline(self, image_path=None, custom_mask_heights=None):
        """
        Sculpts landforms and deep trenches using a combination of Simplex-approx 
        noise curves, radial island falloffs, or direct image-mask interpolation data.
        """
        # Scenario A: Handle custom Image File via PyQt QImage
        if image_path:
            img = QImage(image_path)
            if not img.isNull():
                img = img.scaled(self.width, self.height)
                for cell in self.cells:
                    cx = int(cell["centroid_x"])
                    cy = int(cell["centroid_y"])
                    if 0 <= cx < self.width and 0 <= cy < self.height:
                        pixel = img.pixel(cx, cy)
                        brightness = qRed(pixel)  # use red channel for grayscale proxy
                        # Map brightness 0-255 to height 0-100
                        height = (brightness / 255.0) * 100
                        cell["h"] = int(max(5, min(100, height)))
                return

        for cell in self.cells:
            cid = cell["i"]
            
            # Scenario B: Rely directly on the loaded Land/Ocean grayscale mask image data array
            if custom_mask_heights and cid in custom_mask_heights:
                cell["h"] = custom_mask_heights[cid]
                continue

            # Scenario C: Procedural fractal generation
            cx, cy = cell["centroid_x"], cell["centroid_y"]
            
            # Complex wave overlay noise approximation
            n1 = math.sin(cx * 0.005) * math.cos(cy * 0.005) * 40.0
            n2 = math.sin(cx * 0.02) * math.sin(cy * 0.02) * 15.0
            n3 = math.cos(cx * 0.05) * 5.0
            base_height = 40.0 + n1 + n2 + n3

            # Radial Falloff Mask to form a majestic island cluster
            dist_to_center = math.sqrt((cx - 500)**2 + (cy - 500)**2)
            radial_mask = max(0.0, 1.0 - (dist_to_center / 550.0))
            
            final_h = int(base_height * radial_mask)
            cell["h"] = max(0, min(final_h, 100))

    def run_hydrology_rivers(self):
        """
        Calculates gravity descent drainage flow and traces river vectors
        from highlands down into coastal basins or marine trenches.
        """
        # Sort land cells by elevation descending
        land_cells = [c for c in self.cells if c["h"] >= 20]
        land_cells.sort(key=lambda x: x["h"], reverse=True)

        for cell in land_cells:
            cid = cell["i"]
            lowest_neighbor = -1
            min_h = cell["h"]

            for nid in cell["neighbors"]:
                neighbor = self.cells[nid]
                if neighbor["h"] < min_h:
                    min_h = neighbor["h"]
                    lowest_neighbor = nid

            cell["downhill_neighbor"] = lowest_neighbor

        # Accumulate flow vectors to build river pathways
        for cell in land_cells:
            curr_id = cell["i"]
            flow_vol = 1.0
            
            # Cascade flow down valleys
            while curr_id != -1:
                self.cells[curr_id]["flow_accumulation"] += flow_vol
                downhill = self.cells[curr_id]["downhill_neighbor"]
                if downhill != -1 and self.cells[downhill]["h"] >= 20:
                    curr_id = downhill
                    flow_vol += 0.5
                else:
                    break

        # Instatuate River Segments
        river_counter = 1
        for cell in land_cells:
            if cell["flow_accumulation"] > 15.0:
                cell["river_id"] = river_counter
                river_counter += 1

    def run_biomes_climate(self):
        """
        Applies Hadley atmospheric latitude temperature cells and precipitation vectors.
        Maps the 12 classic land biomes and their exact 12 underwater equivalents.
        """
        for cell in self.cells:
            cy = cell["centroid_y"]
            h = cell["h"]

            # Latitude temperature curve (Cold at poles [0 and 1000], Hot at equator [500])
            latitude_factor = 1.0 - (abs(cy - 500.0) / 500.0)
            base_temp = -10.0 + (latitude_factor * 40.0) # Range -10C to 30C
            
            # Orographic Altitude Lapse Drop
            cell["temp"] = int(base_temp - (h * 0.25))

            # Symmetrical Rain Shadow Moisture propagation
            moisture = int(30 + (math.sin(cy * 0.01) * 30))
            if h > 75: # Rain shadow peak blocking wind currents
                moisture -= 25
            cell["prec"] = max(0, min(moisture, 100))

            # === LAYER CLASSIFICATION RESOLUTION ===
            t = cell["temp"]
            p = cell["prec"]

            if h >= 20:
                # ----------------- TERRESTRIAL BIOMES -----------------
                if h >= 85:
                    cell["biome"] = "Alpine / Mountain"
                elif t < -5:
                    cell["biome"] = "Ice Cap / Glacier" if p > 50 else "Tundra"
                elif t < 5:
                    cell["biome"] = "Cold Desert" if p < 20 else "Taiga"
                elif t < 20:
                    if p < 20:
                        cell["biome"] = "Shrubland / Chaparral"
                    elif p < 50:
                        cell["biome"] = "Steppe / Grassland"
                    else:
                        cell["biome"] = "Temperate Forest"
                else: # Hot Tropics
                    if p < 20:
                        cell["biome"] = "Arid Desert"
                    elif p < 45:
                        cell["biome"] = "Savanna"
                    elif p < 75:
                        cell["biome"] = "Tropical Forest"
                    else:
                        cell["biome"] = "Tropical Rainforest"
            else:
                # ----------------- OCEANIC BIOMES (SYMMETRICAL) -----------------
                # Elevation < 20 is marine. Symmetrical Depth = 20 - H (0 deepest)
                if h <= 4: # Deepest Hadal Trenches / Abyssal plains
                    if t < 0:
                        cell["biome"] = "Abyssal Cryo-Brine Pool"
                    else:
                        cell["biome"] = "Abyssal Barren Desert" if p < 30 else "Benthopelagic Silt Plains"
                elif h < 12: # Bathypelagic Midnight zone
                    if t < 10:
                        cell["biome"] = "Deep Glass Sponge Reef"
                    else:
                        cell["biome"] = "Hydrothermal Chemotrophic Forest"
                else: # Shallow Epipelagic reefs / margins
                    if p < 20:
                        cell["biome"] = "Oceanic Pelagic Barrens"
                    elif p < 45:
                        cell["biome"] = "Sandy Lagoon & Seagrass Bed"
                    elif p < 75:
                        cell["biome"] = "Sunlit Coral Reef"
                    else:
                        cell["biome"] = "Chemosynthetic Thermal Oasis"

    def run_states_expansion(self):
        """
        Seeds political kingdoms on capital cell coordinates and executes a
        Dijkstra cost-field wave propagation to organically grow borders.
        """
        if not self.states:
            return

        # Initialize Dijkstra growth queue
        queue = []
        for state in self.states:
            cap_idx = state["capital"]
            if cap_idx < len(self.cells):
                self.cells[cap_idx]["state"] = state["id"]
                queue.append((0.0, cap_idx, state["id"]))

        # Multi-state wavefront expansion
        while queue:
            # Sort queue by accumulated expansion cost ascending
            queue.sort(key=lambda x: x[0])
            cost, cell_idx, state_id = queue.pop(0)

            cell = self.cells[cell_idx]
            for n_idx in cell["neighbors"]:
                neighbor = self.cells[n_idx]
                if neighbor["state"] == 0: # Unclaimed
                    
                    # Compute Dijkstra friction cost based on geographic barriers
                    elevation_barrier = abs(neighbor["h"] - cell["h"]) * 0.4
                    water_crossing_friction = 15.0 if (neighbor["h"] < 20 and cell["h"] >= 20) else 0.0
                    
                    step_cost = 5.0 + elevation_barrier + water_crossing_friction
                    neighbor["state"] = state_id
                    queue.append((cost + step_cost, n_idx, state_id))

    def sink_generated_world_to_db(self, db_path):
        """Commits all simulated cell, biome, and neighbor variables directly back to SQLite tables."""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Clear old cell coordinate matrices
            cursor.execute("DELETE FROM cells")
            cursor.execute("DELETE FROM cell_cultures_overlap")
            
            for cell in self.cells:
                # 1. Update master coordinates layer
                cursor.execute("""
                    INSERT INTO cells (id, centroid_x, centroid_y, elevation, moisture, temperature, biome, state_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (cell["i"], cell["centroid_x"], cell["centroid_y"], cell["h"], cell["prec"], cell["temp"], cell["biome"], cell["state"] if cell["state"] > 0 else None))
                
                # 2. Update overlapping culture density layer (equal split for seed demo)
                cursor.execute("""
                    INSERT INTO cell_cultures_overlap (cell_id, culture_id, density)
                    VALUES (?, ?, 1.0)
                """, (cell["i"], 50 if cell["h"] >= 20 else 51))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error sinking simulated maps back to DB tables: {e}")
