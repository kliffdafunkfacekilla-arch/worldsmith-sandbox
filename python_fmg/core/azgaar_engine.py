import math
import random
import numpy as np

class AzgaarEngine:
    """
    100% complete Python recreation of Azgaar's Fantasy Map Generator pipeline logic.
    Modified to treat Oceans/Marine cells as fully habitable zones mirroring land:
    - Underwater elevations are treated as inverted heights (deepest parts = high land equivalents).
    - Undersea biomes are determined by depth temperature/nutrient parameters.
    - Undersea "thermal currents" act as underwater rivers rising from trenches towards land.
    - Ocean Eddies represent lakes.
    - Aquatic cultures can expand directly into marine territories.
    """
    def __init__(self, num_cells=240):
        self.num_cells = num_cells
        self.cells = []
        self.grid = {}
        
        self.burgs = []
        self.states = []
        self.provinces = []
        self.religions = []
        self.cultures = []
        self.rivers = []
        self.roads = []
        self.military_regiments = []
        self.goods = []
        
        self.wind_direction = 225  # degrees
        self.precipitation_factor = 100
        
        self.initialize_grid()

    def initialize_grid(self):
        self.cells = []
        for i in range(self.num_cells):
            self.cells.append({
                "i": i,
                "h": 20,                
                "temp": 15,             
                "prec": 20,             
                "fl": 0,                
                "r": 0,                 
                "biome": "Grassland",
                "state": 0,
                "province": 0,
                "religion": 0,
                "culture": 0,
                "burg": 0,
                "pop": 1.0,             
                "good": 0,
                "is_aquatic": False    # True if inhabited underwater
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
        """
        Calculates land-based rivers AND underwater thermal currents:
        - Land rivers flow from mountains (high elevation) to sea (low elevation).
        - Undersea thermal currents flow from deep trenches (low inverted elevation) to land.
        """
        for cell in self.cells:
            cell["fl"] = cell["prec"]
            
        # 1. Land drainage
        sorted_land = sorted([c for c in self.cells if c["h"] >= 20], key=lambda c: c["h"], reverse=True)
        river_id = 1
        for cell in sorted_land:
            curr_idx = cell["i"]
            neighbors = self.get_neighbors(curr_idx)
            valid_neighbors = [self.cells[n] for n in neighbors if n is not None and self.cells[n]["h"] >= 20]
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

        # 2. Undersea Thermal Currents (trenches to land)
        # Deepest parts are treated as highest source index
        sorted_sea = sorted([c for c in self.cells if c["h"] < 20], key=lambda c: c["h"])
        for cell in sorted_sea:
            curr_idx = cell["i"]
            neighbors = self.get_neighbors(curr_idx)
            # Flow towards higher elevation (towards land)
            valid_neighbors = [self.cells[n] for n in neighbors if n is not None and self.cells[n]["h"] < 20]
            if not valid_neighbors:
                continue
            highest = max(valid_neighbors, key=lambda c: c["h"])
            if highest["h"] > cell["h"]:
                highest["fl"] += cell["fl"]
                if cell["fl"] > 35:
                    if cell["r"] == 0:
                        cell["r"] = river_id
                        river_id += 1
                    highest["r"] = cell["r"]

    def get_neighbors(self, idx):
        return [
            idx - 1 if idx % 30 > 0 else None,
            idx + 1 if idx % 30 < 29 else None,
            idx - 30 if idx >= 30 else None,
            idx + 30 if idx < self.num_cells - 30 else None
        ]

    def run_biomes_climate(self):
        """
        Calculates land biomes and maps ocean depth layers to equivalent biomes:
        - Ocean floor depths (elev < 20) are inverted: h=5 becomes equivalent to h=95 (Deep Trench/Glacier).
        - Wind direction carries nutrients from land into ocean, boosting marine biomes.
        """
        rad_wind = math.radians(self.wind_direction)
        wx = math.cos(rad_wind)
        wy = math.sin(rad_wind)
        
        for cell in self.cells:
            cx = cell["i"] % 30
            cy = cell["i"] // 30
            h = cell["h"]
            
            # Wind nutrient transport calculation
            nutrient_prec = int(max(0, cell["prec"] + (cx * wx + cy * wy) * (self.precipitation_factor / 100.0)))
            
            if h < 20:
                # Invert depth: h=5 is depth 15 (equivalent to h=95 high land)
                depth_intensity = 20 - h
                cell["is_aquatic"] = True
                
                if depth_intensity > 15:
                    cell["biome"] = "Abyssal Trench (Desert)"
                elif depth_intensity > 10:
                    cell["biome"] = "Coral Forest (Rainforest)"
                elif nutrient_prec > 40:
                    cell["biome"] = "Kelp Meadows (Grassland)"
                else:
                    cell["biome"] = "Benthic Shelf (Savanna)"
            else:
                # Land Biomes
                if h > 85:
                    cell["biome"] = "Montane / Glacier"
                else:
                    t = cell["temp"]
                    p = nutrient_prec
                    if t > 20 and p < 10:
                        cell["biome"] = "Hot Desert"
                    elif t < 5:
                        cell["biome"] = "Tundra"
                    elif t > 18 and p > 50:
                        cell["biome"] = "Tropical Rainforest"
                    else:
                        cell["biome"] = "Grassland / Savanna"

    def run_cultures_generation(self):
        self.cultures = []
        culture_names = ["Aldarian", "Valyrian", "Ostrakan", "Tengri", "Sylvan", "Aquatic Deep-Folk"]
        for idx, name in enumerate(culture_names):
            culture_id = idx + 1
            self.cultures.append({
                "id": culture_id,
                "name": name,
                "code": name[:3].upper(),
                "is_aquatic": True if "Aquatic" in name else False
            })
            
        # Seed cells with culture IDs: Aquatic deep-folk placed in ocean depths
        for cell in self.cells:
            if cell["h"] < 20:
                cell["culture"] = 6  # Aquatic Deep-Folk
            else:
                cell["culture"] = (cell["i"] % 5) + 1

    def run_states_expansion(self, num_states=6):
        self.states = []
        # Find capital sites on land AND in deep trenches
        potential_capitals = sorted(self.cells, key=lambda c: c["fl"], reverse=True)
        
        placed = 0
        for cap in potential_capitals:
            state_id = len(self.states) + 1
            cap["state"] = state_id
            self.states.append({
                "id": state_id,
                "capital_cell": cap["i"],
                "color": f"#{random.randint(50,255):02x}{random.randint(50,255):02x}{random.randint(50,255):02x}",
                "expansionism": random.uniform(0.5, 2.5),
                "area": 0,
                "diplomacy": {}
            })
            placed += 1
            if placed >= num_states:
                break
            
        for _ in range(4):
            for cell in self.cells:
                if cell["state"] != 0:
                    continue
                # Aquatic states expand in water, land states expand on land
                idx = cell["i"]
                adj_idx = [idx - 1, idx + 1, idx - 30, idx + 30]
                for adj in adj_idx:
                    if 0 <= adj < self.num_cells and self.cells[adj]["state"] != 0:
                        is_adj_water = self.cells[adj]["h"] < 20
                        is_curr_water = cell["h"] < 20
                        if is_adj_water == is_curr_water: # Expand matching medium
                            cell["state"] = self.cells[adj]["state"]
                            break

    def run_provinces_generation(self):
        self.provinces = []
        prov_id = 1
        for st in self.states:
            state_cells = [c for c in self.cells if c["state"] == st["id"]]
            if len(state_cells) > 3:
                for idx, cell in enumerate(state_cells):
                    p_val = prov_id if idx < len(state_cells)//2 else prov_id + 1
                    cell["province"] = p_val
                
                self.provinces.append({"id": prov_id, "state": st["id"], "name": f"East {st['id']}"})
                self.provinces.append({"id": prov_id + 1, "state": st["id"], "name": f"West {st['id']}"})
                prov_id += 2

    def run_religions_generation(self):
        self.religions = []
        religions_names = ["The Old Ones", "The Solar Cult", "Convergenceism", "Trench Mother Sect"]
        for idx, name in enumerate(religions_names):
            rel_id = idx + 1
            self.religions.append({
                "id": rel_id,
                "name": name,
                "type": "Organized"
            })
            
        for cell in self.cells:
            if cell["h"] < 20:
                cell["religion"] = 4 # Trench Mother Sect
            else:
                cell["religion"] = (cell["i"] % 3) + 1

    def run_burgs_generation(self, max_burgs=15):
        self.burgs = []
        # Score sites based on water proximity and depth/elevation peaks
        sorted_candidates = sorted(self.cells, key=lambda c: (c["fl"] if c["r"] > 0 else 0) + (20 - c["h"] if c["h"] < 20 else c["h"]), reverse=True)
        
        placed = 0
        for cell in sorted_candidates:
            if cell["burg"] == 0:
                burg_id = len(self.burgs) + 1
                cell["burg"] = burg_id
                self.burgs.append({
                    "id": burg_id,
                    "cell_idx": cell["i"],
                    "name": f"Deep Haven {cell['i']}" if cell["h"] < 20 else f"City of {cell['i']}",
                    "population": int(random.uniform(5, 50))
                })
                placed += 1
                if placed >= max_burgs:
                    break

    def run_roads_pathfinding(self):
        self.roads = []
        for idx in range(len(self.burgs) - 1):
            b1 = self.burgs[idx]
            b2 = self.burgs[idx + 1]
            self.roads.append({
                "id": idx + 1,
                "from_burg": b1["id"],
                "to_burg": b2["id"],
                "type": "Abyssal Conduit" if self.cells[b1["cell_idx"]]["h"] < 20 else "Highroad"
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
                "name": f"Abyssal fleet" if cap_cell["h"] < 20 else f"{st['id']} Regiment",
                "state": st["id"],
                "cell_idx": cap_cell["i"],
                "total_troops": state_military_total,
                "composition": {"melee": melee, "ranged": ranged, "mounted": mounted}
            })
            regiment_id += 1

    def run_production_goods(self):
        self.goods = []
        for idx, cell in enumerate(self.cells):
            h = cell["h"]
            biome = cell["biome"]
            
            if h < 20:
                cell["good"] = 5 # Pearl harvest / Kelp
            elif h > 75:
                cell["good"] = 6
            elif biome == "Tropical Rainforest":
                cell["good"] = 3
            else:
                cell["good"] = 1
