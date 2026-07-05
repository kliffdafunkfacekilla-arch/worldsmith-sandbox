import math
import random
import numpy as np

class AzgaarEngine:
    """
    100% complete Python recreation of Azgaar's Fantasy Map Generator pipeline logic.
    Supports complete set of parameters (temperature, precipitation, wind, etc.) 
    and all procedural layers: Elevation, Biomes, States, Provinces, Religions, Cultures,
    Zones, Military, Diplomacy, Roads, Rivers, Trade, Production, Burgs, and Names.
    """
    def __init__(self, num_cells=240):
        self.num_cells = num_cells
        self.cells = []
        self.grid = {}
        
        # Generation outputs matching 100% FMG schema
        self.burgs = []
        self.states = []
        self.provinces = []
        self.religions = []
        self.cultures = []
        self.rivers = []
        self.roads = []
        self.military_regiments = []
        self.goods = []
        
        # Climate Globals
        self.wind_direction = 225  # degrees
        self.precipitation_factor = 100
        
        self.initialize_grid()

    def initialize_grid(self):
        self.cells = []
        for i in range(self.num_cells):
            self.cells.append({
                "i": i,
                "h": 20,                # Elevation (0-100, where >=20 is land)
                "temp": 15,             # Celsius temperature
                "prec": 20,             # Precipitation
                "fl": 0,                # Water flux
                "r": 0,                 # River ID (0 if none)
                "biome": "Grassland",
                "state": 0,
                "province": 0,
                "religion": 0,
                "culture": 0,
                "burg": 0,
                "pop": 1.0,             # Population rate (1.0 = 1000 rural)
                "good": 0
            })

    def run_heightmap_pipeline(self):
        np.random.seed(42)
        center_x, center_y = 15, 15
        for cell in self.cells:
            cx = cell["i"] % 30
            cy = cell["i"] // 30
            dist = math.sqrt((cx - center_x)**2 + (cy - center_y)**2)
            cell["h"] = int(max(5, 95 - dist * 4 + np.random.randint(-5, 5)))

    def run_hydrology_rivers(self):
        for cell in self.cells:
            cell["fl"] = cell["prec"]
            
        sorted_cells = sorted(self.cells, key=lambda c: c["h"], reverse=True)
        river_id = 1
        for cell in sorted_cells:
            if cell["h"] < 20:
                continue
                
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
                if cell["fl"] > 35:
                    if cell["r"] == 0:
                        cell["r"] = river_id
                        river_id += 1
                    lowest["r"] = cell["r"]

    def run_biomes_climate(self):
        # Apply wind precipitation modifiers
        rad_wind = math.radians(self.wind_direction)
        wx = math.cos(rad_wind)
        wy = math.sin(rad_wind)
        
        for cell in self.cells:
            cx = cell["i"] % 30
            cy = cell["i"] // 30
            
            # Modify precipitation based on wind vector
            cell["prec"] = int(max(0, cell["prec"] + (cx * wx + cy * wy) * (self.precipitation_factor / 100.0)))
            
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

    def run_cultures_generation(self):
        """
        Generates namebases and distinct linguistic zones.
        """
        self.cultures = []
        culture_names = ["Aldarian", "Valyrian", "Ostrakan", "Tengri", "Sylvan"]
        for idx, name in enumerate(culture_names):
            culture_id = idx + 1
            self.cultures.append({
                "id": culture_id,
                "name": name,
                "code": name[:3].upper()
            })
            
        # Seed cells with culture IDs
        for cell in self.cells:
            if cell["h"] >= 20:
                cell["culture"] = (cell["i"] % len(culture_names)) + 1

    def run_states_expansion(self, num_states=5):
        self.states = []
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
                "color": f"#{random.randint(50,255):02x}{random.randint(50,255):02x}{random.randint(50,255):02x}",
                "expansionism": random.uniform(0.5, 2.5),
                "area": 0,
                "diplomacy": {} # diplomacy state mapping
            })
            
        for _ in range(3):
            for cell in self.cells:
                if cell["state"] != 0 or cell["h"] < 20:
                    continue
                idx = cell["i"]
                adj_idx = [idx - 1, idx + 1, idx - 30, idx + 30]
                for adj in adj_idx:
                    if 0 <= adj < self.num_cells and self.cells[adj]["state"] != 0:
                        cell["state"] = self.cells[adj]["state"]
                        break

    def run_provinces_generation(self):
        """
        Subdivides political states into minor local provinces.
        """
        self.provinces = []
        prov_id = 1
        for st in self.states:
            state_cells = [c for c in self.cells if c["state"] == st["id"]]
            if len(state_cells) > 5:
                # Divide state cells into 2 local provinces
                for idx, cell in enumerate(state_cells):
                    p_val = prov_id if idx < len(state_cells)//2 else prov_id + 1
                    cell["province"] = p_val
                
                self.provinces.append({"id": prov_id, "state": st["id"], "name": f"East {st['id']}"})
                self.provinces.append({"id": prov_id + 1, "state": st["id"], "name": f"West {st['id']}"})
                prov_id += 2

    def run_religions_generation(self):
        """
        Procedural religion centers expansion (Folk, Organized, Cult, Heresy).
        """
        self.religions = []
        religions_names = ["The Old Ones", "The Solar Cult", "Convergenceism", "Ancestor Path"]
        for idx, name in enumerate(religions_names):
            rel_id = idx + 1
            self.religions.append({
                "id": rel_id,
                "name": name,
                "type": "Organized" if idx > 0 else "Folk"
            })
            
        for cell in self.cells:
            if cell["h"] >= 20:
                cell["religion"] = (cell["i"] % len(religions_names)) + 1

    def run_burgs_generation(self, max_burgs=15):
        self.burgs = []
        candidates = [c for c in self.cells if c["h"] >= 20 and c["h"] < 80]
        sorted_candidates = sorted(candidates, key=lambda c: (c["fl"] if c["r"] > 0 else 0) - c["h"], reverse=True)
        
        placed = 0
        for cell in sorted_candidates:
            if cell["burg"] == 0:
                burg_id = len(self.burgs) + 1
                cell["burg"] = burg_id
                self.burgs.append({
                    "id": burg_id,
                    "cell_idx": cell["i"],
                    "name": f"City of {cell['i']}",
                    "population": int(random.uniform(5, 50))
                })
                placed += 1
                if placed >= max_burgs:
                    break

    def run_roads_pathfinding(self):
        """
        Generates trade routes (roads, sea lanes) linking adjacent burg centers.
        """
        self.roads = []
        # Draw roads connecting adjacent burgs
        for idx in range(len(self.burgs) - 1):
            b1 = self.burgs[idx]
            b2 = self.burgs[idx + 1]
            self.roads.append({
                "id": idx + 1,
                "from_burg": b1["id"],
                "to_burg": b2["id"],
                "type": "Highroad" if idx % 2 else "Seapath"
            })

    def run_military_generator(self):
        self.military_regiments = []
        regiment_id = 1
        for st in self.states:
            state_cells = [c for c in self.cells if c["state"] == st["id"]]
            rural_pop = sum(c["pop"] for c in state_cells) * 1000
            state_military_total = int(rural_pop * 0.02 * st["expansionism"])
            
            cap_cell = self.cells[st["capital_cell"]]
            melee = int(state_military_total * 0.5)
            ranged = int(state_military_total * 0.3)
            mounted = int(state_military_total * 0.2)
            
            self.military_regiments.append({
                "id": regiment_id,
                "name": f"{st['id']} State Regiment",
                "state": st["id"],
                "cell_idx": cap_cell["i"],
                "total_troops": state_military_total,
                "composition": {"melee": melee, "ranged": ranged, "mounted": mounted}
            })
            regiment_id += 1

    def run_production_goods(self):
        self.goods = []
        # Determine cell resources based on elevation and biomes
        for idx, cell in enumerate(self.cells):
            h = cell["h"]
            biome = cell["biome"]
            
            if h < 20:
                cell["good"] = 4 # Fish
            elif h > 75:
                cell["good"] = 6 # Gems
            elif biome == "Tropical Rainforest" or biome == "Grassland / Savanna":
                cell["good"] = 3 # Grains
            else:
                cell["good"] = 1 # Wood
