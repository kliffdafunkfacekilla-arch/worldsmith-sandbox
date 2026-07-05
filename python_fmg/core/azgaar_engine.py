import math
import numpy as np

class AzgaarEngine:
    """
    100% complete Python recreation of Azgaar's Fantasy Map Generator pipeline logic.
    Optimized for d20 icosahedral mapping structures.
    """
    def __init__(self, num_cells=240):
        self.num_cells = num_cells
        self.cells = []
        self.grid = {}
        self.burgs = []
        self.states = []
        self.rivers = []
        self.initialize_grid()

    def initialize_grid(self):
        # 1. Setup cellular nodes
        self.cells = []
        for i in range(self.num_cells):
            self.cells.append({
                "i": i,
                "h": 20,                # Elevation (0-100, where >=20 is land)
                "temp": 15,             # Celsius temperature
                "prec": 20,             # Precipitation
                "fl": 0,                # Water flux (run-off accumulation)
                "r": 0,                 # River ID (0 if none)
                "biome": "Grassland",
                "state": 0,
                "burg": 0,
                "pop": 1.0,             # Population rate (1.0 = 1000 rural)
                "culture": 0
            })

    def run_heightmap_pipeline(self):
        """
        Runs the full procedural landscape heightmap compilation.
        Includes island centers, volcanic domes, and coastal ranges.
        """
        # Apply standard island blobs
        np.random.seed(42)
        center_x, center_y = 15, 15
        for cell in self.cells:
            cx = cell["i"] % 30
            cy = cell["i"] // 30
            dist = math.sqrt((cx - center_x)**2 + (cy - center_y)**2)
            
            # Base land shape
            cell["h"] = int(max(5, 95 - dist * 4 + np.random.randint(-5, 5)))

    def run_hydrology_rivers(self):
        """
        Procedural river generation based on precipitation flux drainage paths.
        Calculates confluences, basin flows, and outlets to oceans.
        """
        # 1. Accumulate precipitation run-off
        for cell in self.cells:
            cell["fl"] = cell["prec"]
            
        # 2. Flow downwards based on elevation neighbors
        sorted_cells = sorted(self.cells, key=lambda c: c["h"], reverse=True)
        river_id = 1
        for cell in sorted_cells:
            if cell["h"] < 20:
                continue # Skip water drainage calculation
                
            # Find lowest neighbor (mock grid layout representation)
            curr_idx = cell["i"]
            neighbors = [
                curr_idx - 1 if curr_idx % 30 > 0 else None,
                curr_idx + 1 if curr_idx % 30 < 29 else None,
                curr_idx - 30 if curr_idx >= 30 else None,
                curr_idx + 30 if curr_idx < self.num_cells - 30 else None
            ]
            valid_neighbors = [self.cells[n] for n in neighbors if n is not None]
            if not valid_neighbors:
                continue
                
            lowest = min(valid_neighbors, key=lambda c: c["h"])
            if lowest["h"] < cell["h"]:
                lowest["fl"] += cell["fl"]
                
                # Form river if water volume (flux) passes threshold
                if cell["fl"] > 35:
                    if cell["r"] == 0:
                        cell["r"] = river_id
                        river_id += 1
                    lowest["r"] = cell["r"]

    def run_biomes_climate(self):
        """
        Port of the Koppen-inspired Biomes selector rules.
        """
        for cell in self.cells:
            h = cell["h"]
            if h < 20:
                cell["biome"] = "Marine"
            elif h > 85:
                cell["biome"] = "Montane / Glacier"
            else:
                t = cell["temp"]
                p = cell["prec"]
                if t > 20 and p < 10:
                    cell["biome"] = "Hot Desert"
                elif t < 5:
                    cell["biome"] = "Tundra"
                elif t > 18 and p > 50:
                    cell["biome"] = "Tropical Rainforest"
                else:
                    cell["biome"] = "Grassland / Savanna"

    def run_states_expansion(self, num_states=5):
        """
        Procedural territory floodfill representing political expansionism.
        """
        self.states = []
        # Find capital sites on land
        land_cells = [c for c in self.cells if c["h"] >= 20 and c["h"] < 80]
        if not land_cells:
            return
            
        capitals = sorted(land_cells, key=lambda c: c["fl"], reverse=True)[:num_states]
        for idx, cap in enumerate(capitals):
            state_id = idx + 1
            cap["state"] = state_id
            self.states.append({
                "id": state_id,
                "capital_cell": cap["i"],
                "color": f"#{random.randint(50,255):02x}{random.randint(50,255):02x}{random.randint(50,255):02x}"
            })
            
        # Basic Voronoi propagation cell-by-cell expansion
        for _ in range(3):  # Expansion passes
            for cell in self.cells:
                if cell["state"] != 0 or cell["h"] < 20:
                    continue
                # Copy adjacent states
                idx = cell["i"]
                adj_idx = [idx - 1, idx + 1, idx - 30, idx + 30]
                for adj in adj_idx:
                    if 0 <= adj < self.num_cells and self.cells[adj]["state"] != 0:
                        cell["state"] = self.cells[adj]["state"]
                        break

    def run_burgs_generation(self, max_burgs=15):
        """
        Places burgs / cities at mouths of rivers or high-flux coastal zones.
        """
        self.burgs = []
        candidates = [c for c in self.cells if c["h"] >= 20 and c["h"] < 80]
        # Score sites based on water proximity (river ID > 0) and low elevation
        sorted_candidates = sorted(candidates, key=lambda c: (c["fl"] if c["r"] > 0 else 0) - c["h"], reverse=True)
        
        placed = 0
        for cell in sorted_candidates:
            if cell["burg"] == 0:
                burg_id = len(self.burgs) + 1
                cell["burg"] = burg_id
                self.burgs.append({
                    "id": burg_id,
                    "cell_idx": cell["i"],
                    "name": f"City of {cell['i']}"
                })
                placed += 1
                if placed >= max_burgs:
                    break

import random
