import math
import random
import sqlite3
import json

class CosmosEngine:
    """Manages astronomical timelines, seasons, and celestial tracking variables."""
    def __init__(self, year_length=420, seasons=None):
        self.year_length = year_length
        self.seasons = seasons if seasons else ["Sowing", "High-Sun", "Gold-Leaf", "Deep-Frost"]
        
    def get_current_season(self, day_of_year):
        """Maps absolute day of year to corresponding seasonal quadrant."""
        quadrant = int((day_of_year % self.year_length) / (self.year_length / len(self.seasons)))
        return self.seasons[min(quadrant, len(self.seasons) - 1)]


class AzgaarEngine:
    """
    Simulates physical planetary geology, climatology, and structural boundaries.
    Connects database lore constraints to procedural cell matrices.
    """
    def __init__(self):
        self.cells = []
        self.states = []
        self.cultures = []
        self.religions = []
        self.burgs = []
        self.width = 1000
        self.height = 1000

    def generate_voronoi_mesh(self, num_cells=1000):
        """
        Creates an organic mesh of connected points using jittered spatial grids.
        Avoids external SciPy dependencies while delivering natural Voronoi behavior.
        """
        self.cells = []
        grid_size = int(math.sqrt(num_cells))
        spacing_x = self.width / grid_size
        spacing_y = self.height / grid_size

        # Create jittered points
        cell_id = 0
        for r in range(grid_size):
            for c in range(grid_size):
                jx = random.uniform(-spacing_x * 0.4, spacing_x * 0.4)
                jy = random.uniform(-spacing_y * 0.4, spacing_y * 0.4)
                
                cx = (c * spacing_x) + (spacing_x / 2) + jx
                cy = (r * spacing_y) + (spacing_y / 2) + jy
                
                self.cells.append({
                    "i": cell_id,
                    "centroid_x": max(10, min(self.width - 10, cx)),
                    "centroid_y": max(10, min(self.height - 10, cy)),
                    "neighbors": [],
                    "h": 20,          # Height baseline (20 = Shoreline)
                    "temp": 15,        # Temperature Celsius
                    "prec": 10,        # Precipitation/Moisture
                    "biome": "Marine", # Whittaker Class
                    "state": 0,        # Political Sovereign (0 = Neutral)
                    "province": 0,     # Province Layer
                    "culture": 0,      # Ethno-culture Layer
                    "religion": 0      # Holy expansion space
                })
                cell_id += 1

        # Calculate cell connections based on distance proximity
        for i in range(len(self.cells)):
            c1 = self.cells[i]
            dists = []
            for j in range(len(self.cells)):
                if i == j: continue
                c2 = self.cells[j]
                d = math.hypot(c1["centroid_x"] - c2["centroid_x"], c1["centroid_y"] - c2["centroid_y"])
                dists.append((d, j))
            
            # Keep nearest 6-8 coordinates as Voronoi neighbors
            dists.sort()
            neighbors_count = random.randint(5, 7)
            c1["neighbors"] = [idx for (_, idx) in dists[:neighbors_count]]

    def run_heightmap_pipeline(self):
        """
        Applies a multi-octave island heightmask over the mesh.
        Creates organic continents, coastal shelves, and rugged mountain spines.
        """
        center_x = self.width / 2
        center_y = self.height / 2
        max_dist = math.hypot(center_x, center_y)

        for cell in self.cells:
            cx = cell["centroid_x"]
            cy = cell["centroid_y"]
            
            # Island radial falloff mask
            dist_to_center = math.hypot(cx - center_x, cy - center_y)
            radial_factor = 1.0 - (dist_to_center / max_dist)
            radial_factor = max(0.0, radial_factor)

            # Layered mathematical wave noise
            noise_val = (
                math.sin(cx * 0.008) * math.cos(cy * 0.008) * 40 +
                math.sin(cx * 0.02) * math.cos(cy * 0.015) * 15 +
                math.sin(cx * 0.05) * math.cos(cy * 0.05) * 5
            )
            
            # Combine raw height with radial mask
            height = (radial_factor * 60) + noise_val
            
            # Determine mountain chains along linear offsets
            spine_dist = abs(cy - (self.height * 0.5) - math.sin(cx * 0.01) * 150)
            if spine_dist < 120 and height > 20:
                mountain_spine = (1.0 - (spine_dist / 120)) * 35
                height += mountain_spine
                
            cell["h"] = int(max(5, min(100, height)))

    def run_biomes_climate(self, wind_angle_deg=45):
        """
        Runs the 7-band Hadley wind model and Orographic precipitation loop.
        Classifies ecosystems using the Whittaker model.
        """
        wind_rad = math.radians(wind_angle_deg)
        wind_dx = math.cos(wind_rad)
        wind_dy = math.sin(wind_rad)

        # Sort cells along the primary wind axis to trace rain accumulation
        sorted_cells = sorted(self.cells, key=lambda c: (c["centroid_x"] * wind_dx + c["centroid_y"] * wind_dy))

        for cell in sorted_cells:
            # Baseline temperature derived from latitude (Y) and elevation lapse rate
            lat_pct = cell["centroid_y"] / self.height
            baseline_temp = 35.0 - (lat_pct * 40.0)  # Hot Equator (top), Cold Polar (bottom)
            lapse_rate_drop = (cell["h"] / 100.0) * 18.0
            cell["temp"] = int(baseline_temp - lapse_rate_drop)

            # Trace moisture carrying winds
            upwind_moisture = 40.0 if cell["h"] < 20 else 25.0
            
            # Look up upwind neighbor's elevation to simulate Orographic Lift (Rain Shadows)
            for neighbor_idx in cell["neighbors"]:
                neighbor = self.cells[neighbor_idx]
                height_delta = cell["h"] - neighbor["h"]
                if height_delta > 10:  # Climbing peak: dump rain
                    upwind_moisture -= height_delta * 0.4
                    cell["prec"] += int(height_delta * 0.8)
            
            cell["prec"] = int(max(0, min(100, upwind_moisture + cell["prec"])))

            # Whittaker Biome Matrix
            h = cell["h"]
            t = cell["temp"]
            p = cell["prec"]

            if h < 20:
                cell["biome"] = "Marine"
            elif t < 0:
                cell["biome"] = "Ice Cap" if p > 50 else "Tundra"
            elif t < 10:
                cell["biome"] = "Boreal Forest" if p > 30 else "Cold Desert"
            elif t < 22:
                if p < 15: cell["biome"] = "Arid Desert"
                elif p < 45: cell["biome"] = "Shrubland"
                else: cell["biome"] = "Temperate Forest"
            else:
                if p < 20: cell["biome"] = "Arid Desert"
                elif p < 50: cell["biome"] = "Savanna"
                else: cell["biome"] = "Tropical Rainforest"

    def run_hydrology_rivers(self):
        """
        Traces continuous water flow downhill to ocean basins.
        Computes flow accumulation matrices per coordinate cell.
        """
        # Reset flow values
        for cell in self.cells:
            cell["river_id"] = 0
            cell["flow"] = 1.0

        # Sort cells highest to lowest
        sorted_cells = sorted(self.cells, key=lambda c: c["h"], reverse=True)

        for cell in sorted_cells:
            if cell["h"] < 20: continue # Skip sea level
            
            # Find the lowest adjacent neighbor
            lowest_neighbor = None
            min_height = cell["h"]
            
            for n_idx in cell["neighbors"]:
                n = self.cells[n_idx]
                if n["h"] < min_height:
                    min_height = n["h"]
                    lowest_neighbor = n
            
            # Route flow downhill
            if lowest_neighbor:
                lowest_neighbor["flow"] += cell["flow"]

    def run_states_expansion(self):
        """
        Grows political factions outward from designated capitals.
        Applies Cost-field Dijkstra navigation over mountains and different cultures.
        """
        # Standard fallback if no factions exist inside the active workspace
        if not self.states:
            self.states = [
                {"id": 1, "name": "Vulfurn Empire", "color": "#ef4444", "capital": 250},
                {"id": 2, "name": "Chipis Hegemony", "color": "#3b82f6", "capital": 750}
            ]

        # Reset cell states
        for cell in self.cells:
            cell["state"] = 0

        # Initialize Dijkstra growth queue
        frontier = []
        costs = {}

        # Seed capital cells
        for state in self.states:
            cap_idx = state.get("capital", random.randint(100, 800))
            # Keep bounds safe
            cap_idx = min(max(0, cap_idx), len(self.cells) - 1)
            
            self.cells[cap_idx]["state"] = state["id"]
            frontier.append((0.0, cap_idx, state["id"]))
            costs[cap_idx] = 0.0

        # Expand frontier
        while frontier:
            frontier.sort()
            curr_cost, curr_idx, state_id = frontier.pop(0)
            
            curr_cell = self.cells[curr_idx]
            if curr_cost > costs.get(curr_idx, 9999.0): continue

            for n_idx in curr_cell["neighbors"]:
                neighbor = self.cells[n_idx]
                if neighbor["h"] < 20: continue # Mountain shelves block sea expansion
                
                # Height friction penalty
                elevation_cost = max(1.0, neighbor["h"] - curr_cell["h"])
                step_cost = 1.0 + (elevation_cost * 0.1)
                new_cost = curr_cost + step_cost
                
                if new_cost < costs.get(n_idx, 9999.0):
                    costs[n_idx] = new_cost
                    neighbor["state"] = state_id
                    frontier.append((new_cost, n_idx, state_id))

    def run_cultures_generation(self):
        """Stubs out default cultures list."""
        self.cultures = [
            {"id": 1, "name": "Ostrakan", "code": "OS"},
            {"id": 2, "name": "Boreal Elven", "code": "BE"}
        ]
        # Seed cells with cultures based on distance to poles
        for cell in self.cells:
            cell["culture"] = 1 if cell["centroid_y"] < self.height * 0.5 else 2

    def run_religions_generation(self):
        self.religions = [
            {"id": 1, "name": "Worship of Dawn", "supreme_deity": "Solis"}
        ]
        for cell in self.cells:
            cell["religion"] = 1

    def run_burgs_generation(self):
        """Places settlements on high-habitability cells (near water and flat land)."""
        self.burgs = []
        burg_id = 1
        
        # Place up to 15 burgs
        for cell in self.cells:
            if len(self.burgs) >= 15: break
            if cell["h"] >= 20 and cell["h"] < 45: # Flat land above sea level
                # Proximity check
                too_close = False
                for b in self.burgs:
                    other_cell = self.cells[b["cell_idx"]]
                    dist = math.hypot(cell["centroid_x"] - other_cell["centroid_x"], cell["centroid_y"] - other_cell["centroid_y"])
                    if dist < 120: too_close = True
                
                if not too_close:
                    self.burgs.append({
                        "id": burg_id,
                        "name": f"Burg_{burg_id}",
                        "population": random.randint(8, 28),
                        "state": cell["state"],
                        "cell_idx": cell["i"],
                        "culture": cell["culture"]
                    })
                    burg_id += 1

    def run_roads_pathfinding(self): pass
    def run_trade_and_market_simulation(self): pass
    def run_military_generator(self): pass
    def run_production_goods(self): pass
    def slice_state_provinces(self): pass
    def run_diplomacy_matrix_engine(self): pass

    def sink_generated_world_to_db(self, db_path):
        """Commits all procedural grid cells, elevations, and states into the relational SQL tables."""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Step A: Purge old coordinates cache
            cursor.execute("DELETE FROM cells")
            cursor.execute("DELETE FROM cell_neighbors")
            
            # Step B: Insert cell rows
            for c in self.cells:
                cursor.execute("""
                    INSERT INTO cells (id, centroid_x, centroid_y, elevation, moisture, temperature, state_id, province_id, culture_id, religion_id, biome)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    c["i"], c["centroid_x"], c["centroid_y"], c["h"], c["prec"], c["temp"],
                    c["state"] if c["state"] > 0 else None,
                    c["province"] if c["province"] > 0 else None,
                    c["culture"] if c["culture"] > 0 else None,
                    c["religion"] if c["religion"] > 0 else None,
                    c["biome"]
                ))
                
                # Insert neighbor pairs
                for n_idx in c["neighbors"]:
                    cursor.execute("""
                        INSERT OR IGNORE INTO cell_neighbors (cell_id, neighbor_id)
                        VALUES (?, ?)
                    """, (c["i"], n_idx))

            # Step C: Re-sync settlements/burgs table with coordinate anchors
            cursor.execute("DELETE FROM settlements")
            for b in self.burgs:
                cursor.execute("""
                    INSERT INTO settlements (name, population, cell_idx, faction_id, culture_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    b["name"], b["population"], b["cell_idx"],
                    b["state"] if b["state"] > 0 else None,
                    b["culture"] if b["culture"] > 0 else None
                ))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error sinking map cells to SQL database: {e}")
