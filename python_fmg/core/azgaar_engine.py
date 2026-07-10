import math
import random
import heapq
import sqlite3
import json
import numpy as np
from scipy.spatial import Voronoi

class CosmosEngine:
    def __init__(self, year_length=420, seasons=None, moons=None):
        self.year_length = year_length
        self.seasons = seasons or ["Sowing-Time", "High-Sun", "Gold-Leaf", "Deep-Frost"]
        self.moons = moons or [
            {"name": "Sari", "period": 14.0, "radius": 120},
            {"name": "Ostra", "period": 28.0, "radius": 240}
        ]
        
    def get_cosmic_state(self, current_day):
        progress = (current_day - 1) / self.year_length
        season_idx = int(progress * len(self.seasons))
        current_season = self.seasons[min(season_idx, len(self.seasons)-1)]
        solar_angle = progress * 2 * math.pi
        
        state = {
            "season": current_season,
            "solar_angle": math.degrees(solar_angle),
            "moons": [],
            "stars": []
        }
        
        for m in self.moons:
            moon_phase_angle = (current_day % m["period"]) / m["period"] * 2 * math.pi
            mx = m["radius"] * math.cos(moon_phase_angle)
            my = m["radius"] * math.sin(moon_phase_angle)
            
            state["moons"].append({
                "name": m["name"],
                "x": mx, "y": my,
                "phase_pct": (current_day % m["period"]) / m["period"]
            })
            
        base_constellations = ["The Leviathan", "The Mage Node", "The High Sovereign", "The Abyss"]
        for idx, name in enumerate(base_constellations):
            star_angle = (idx * (2 * math.pi / len(base_constellations))) + solar_angle
            state["stars"].append({
                "name": name,
                "angle": math.degrees(star_angle) % 360
            })
            
        return state

    def update_celestial_magic_flux(self, db_path, current_day):
        if not self.moons:
            return 1.0
            
        phases = [(current_day % m["period"]) / m["period"] for m in self.moons]
        is_aligned = False
        if len(phases) >= 2:
            p0 = phases[0]
            aligned_count = 1
            for p in phases[1:]:
                diff = abs(p0 - p)
                if diff < 0.05 or abs(diff - 0.5) < 0.05:
                    aligned_count += 1
            if aligned_count == len(phases):
                is_aligned = True
                
        ambient_multiplier = 2.5 if is_aligned else 1.0
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO world_cosmology (day_index, season, active_constellation, magic_multiplier)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(day_index) DO UPDATE SET magic_multiplier=excluded.magic_multiplier
            """, (current_day, "Dynamic", "The Mage Node", ambient_multiplier))
            conn.commit()
            conn.close()
        except:
            pass
            
        return ambient_multiplier

class MarkovNameGenerator:
    """
    Advanced Markov-Chain nomenclature class driven by the 6 expanded Ostraka seed pools.
    """
    def __init__(self):
        self.configs = {
            "Ostraka Mammalian": ["Snowpeak", "Viomuth", "Stagus", "Koda", "Daniaz", "Bramun", "Grooth", "Sturn", "Vulfen", "Hirthrost", "Kodmuth", "Shareg", "Muthurn", "Bramkoda", "Vulfrost", "Sturnden", "Grothun", "Muthrost", "Kodan", "Hirshmuth", "Staghirth", "Vulfmuth", "Oakhaven", "Whiskers", "Mungo", "Hargus", "Horgus", "Griss", "Hirth", "Bramm", "Oona", "Vulpus", "Simia", "Ailurus", "Vulparyn", "Tarsinus", "Shalach", "Lynari", "Zimax", "Felynx", "Shalari", "Tarsimax", "Vulpis", "Lynax", "Zilutes", "Charyb", "Simreach", "Ailuryn", "Vulpbough", "Tarsich", "Zylari", "Felynari", "Equus", "Stag", "Chipper", "Keth", "Forgerost"],
            "Ostraka Reptilian": ["Carulkem", "Szarax", "Ignis", "Slush", "Skat", "Tiraton", "Grom", "Carulk", "Szaraxen", "Ignulkem", "Slussh", "Skatalon", "Grompit", "Tiratelon", "Carupit", "Szatalon", "Ignirax", "Sluax", "Skatgate", "Gromgate", "Carurax", "Lophex", "Rictus", "Vahn", "Eldra", "Frilled", "Skink", "Gromit", "Osmium", "Tungsten", "Titanium", "Bismuth", "Chromium", "Szamire", "Carulsh", "Ignisston", "Szaraxgate", "Tiratulkem", "Slushpit", "Skatalon", "Gromulsh", "Carulskat", "Szignis"],
            "Ostraka Avian": ["Excelsis", "Aurelius", "Kaelos", "Hrothe", "Kaelen", "Vira", "Liora", "Lophex", "Krara", "Hrothes", "Caelios", "Skavax", "Kraeon", "Phraxos", "Traron", "Quorax", "Vauxit", "Tsarnth", "Phraeth", "Kracer", "Caelith", "Viraon", "Hrotham", "Skalor", "Fulcrum", "Aethel", "Erranith", "Condor", "Orestes", "Kaelon", "Phrax", "Roost", "Vanecon", "Skiff", "Aetherium", "Prism", "Summit", "Hrothit", "Caelrax", "Skavir", "Hrotheon", "Caelosnia", "Phraxosrix", "Viraeth", "Kraron", "Trarax", "Quorith", "Vauxos"],
            "Ostraka Insectoid": ["Valkor", "Tyrustis", "Zeila", "Tyrzith", "Vthka", "Kuaix", "Slit", "Zca", "Xytis", "Chaka", "Tkmurex", "Slizith", "Vca", "Xyca", "Tyrka", "Ktis", "Murexca", "Zithka", "Slitk", "Xyzith", "Tyruaix", "Kthka", "Slca", "Tkzith", "Formica", "Mantis", "Scorpion", "Chitin", "Murex", "Quartz", "Zithis", "Xytk", "Tkatcon", "Slitex", "Vcon", "Xyda", "Tyrax", "Ktweb", "Murexis", "Zithweb", "Slitda", "Xytcon", "Tyrcon", "Ktext", "Murexta", "Zitht", "Slitcon", "Xyis"],
            "Ostraka Aquatic": ["Cruorbus", "Boudreaux", "Gavusrix", "Jax", "Felix", "Moir", "Slumire", "Gavus", "Boudaux", "Vyrnax", "Gumbo", "Gavg glub", "Mirekin", "Vyrdaux", "Slugumbo", "Boudmire", "Gavkin", "Moirusrix", "Vyrusrix", "Glubkin", "Boudusrix", "Sludaux", "Undine", "Malaki", "Seahorse", "Whale", "Dolphin", "Snail", "Opalwallow", "Benthic", "Sumpkin", "Mire", "Cruor", "Aetheric", "Backwash", "Meander", "Vortex", "Delta", "Abyssal", "Pelagic", "Trench", "Shelf", "Coral", "Kelp"],
            "Ostraka Botanical": ["Arbor", "Sylvan", "Vecelo", "Emerald", "Scar", "Roots", "Bough", "Glen", "Thicket", "Brambles", "Briar", "Yucca", "Cactus", "Tumbleweed", "Moonflower", "Grave-Root", "Arbor-Prime", "Sylvscar", "Vecelobough", "Emerglen", "Scarthicket", "Rootbrambles", "Briaryucca", "Cactusbough", "Tumbleglen", "Moonthicket", "Gravescar", "Arborbough", "Sylvglen", "Vecelothicket", "Emerbrambles", "Scaryucca", "Rootcactus", "Briartumble", "Cactusmoon", "Tumblegrave", "Moonglen"]
        }

    def generate_name(self, profile_key):
        # Generate word using segment pairs from seed arrays
        pool = self.configs.get(profile_key, self.configs["Ostraka Mammalian"])
        if not pool:
            return "Ostraka"
        words = random.sample(pool, min(2, len(pool)))
        part1 = words[0][:len(words[0])//2]
        part2 = words[1][len(words[1])//2:]
        return (part1 + part2).capitalize()

class AzgaarEngine:
    """
    100% complete Python recreation of Azgaar's Fantasy Map Generator pipeline logic
    upgraded to use a mathematically robust, high-performance irregular Voronoi mesh layout.
    """
    def __init__(self, num_points=10000, width=800, height=600):
        self.num_points = num_points
        self.width = width
        self.height = height
        
        self.cells = []
        self.burgs = []
        self.states = []
        self.provinces_pool = {}
        self.religions = []
        self.cultures = []
        self.rivers = []
        self.roads = []
        self.military_regiments = []
        self.zones = []
        
        self.name_gen = MarkovNameGenerator()
        # Voronoi mesh is no longer generated automatically on init.
        # Call generate_voronoi_mesh() explicitly to create a new map.

    def generate_voronoi_mesh(self):
        np.random.seed(42)
        # Generate initial random points within the canvas
        points = np.column_stack((
            np.random.uniform(20, self.width - 20, self.num_points),
            np.random.uniform(20, self.height - 20, self.num_points)
        ))
        
        # Create bounding dummy points far outside the canvas to close all regions inside the canvas
        w, h = self.width, self.height
        bounding_points = np.array([
            [-w, -h], [2*w, -h], [2*w, 2*h], [-w, 2*h],
            [w/2, -h], [w/2, 2*h], [-w, h/2], [2*w, h/2]
        ])
        
        for _ in range(2):
            all_points = np.vstack((points, bounding_points))
            vor = Voronoi(all_points)
            new_points = []
            
            # Only relax the real points (indices 0 to num_points - 1)
            for i in range(self.num_points):
                region_idx = vor.point_region[i]
                region = vor.regions[region_idx]
                if not region or -1 in region:
                    # Should rarely happen for internal points due to bounding dummy points
                    new_points.append(points[i])
                else:
                    poly = vor.vertices[region]
                    # Clamp the relaxed point to stay within bounds
                    center = poly.mean(axis=0)
                    cx = np.clip(center[0], 5, self.width - 5)
                    cy = np.clip(center[1], 5, self.height - 5)
                    new_points.append([cx, cy])
                    
            points = np.array(new_points)

        # Final Voronoi with relaxed points and bounding points
        all_points = np.vstack((points, bounding_points))
        self.vor_mesh = Voronoi(all_points)
        
        self.cells = []
        for i in range(self.num_points):
            pt = points[i]
            self.cells.append({
                "i": i,
                "x": float(pt[0]),
                "y": float(pt[1]),
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
                "good": "None",
                "is_aquatic": False,
                "zone": 0
            })
            
        self._precompute_neighbors()

    def run_heightmap_pipeline(self):
        center_x, center_y = self.width / 2.0, self.height / 2.0
        max_dist = math.sqrt(center_x**2 + center_y**2)
        
        seed_x = random.uniform(100.0, 5000.0)
        seed_y = random.uniform(100.0, 5000.0)
        
        for cell in self.cells:
            nx = (cell["x"] / self.width) + seed_x
            ny = (cell["y"] / self.height) + seed_y
            
            val = 0.0
            freq = 1.0
            amp = 1.0
            for _ in range(4): 
                val += math.sin(nx * freq * 4.0) * math.cos(ny * freq * 4.0) * amp
                freq *= 2.2
                amp *= 0.5
                
            noise_factor = (val + 1.5) / 3.0 * 50.0
            dist_to_core = math.sqrt((cell["x"] - center_x)**2 + (cell["y"] - center_y)**2)
            island_mask = 1.0 - (dist_to_core / (max_dist * 0.75))
            island_mask = max(0.0, min(1.0, island_mask))
            
            final_h = (noise_factor * 0.6) + (island_mask * 60.0)
            clamped_h = int(max(5, min(98, final_h)))
            cell["h"] = clamped_h

    def apply_height_brush(self, center_idx, radius, tool_mode, intensity=5):
        visited = {center_idx}
        queue = [(center_idx, 0)]
        affected = []
        
        # Gather cells in radius
        while queue:
            curr, dist = queue.pop(0)
            affected.append((curr, dist))
            if dist < radius - 1:
                for n in self.get_neighbors(curr):
                    if n not in visited:
                        visited.add(n)
                        queue.append((n, dist + 1))
                        
        if tool_mode == "Height Smooth":
            original_heights = {cell_id: self.cells[cell_id]["h"] for cell_id, _ in affected}
            for cell_id, _ in affected:
                neighbors = self.get_neighbors(cell_id)
                avg_h = sum(self.cells[n]["h"] for n in neighbors) / len(neighbors)
                self.cells[cell_id]["h"] = int((original_heights[cell_id] + avg_h) / 2)
        else:
            for cell_id, dist in affected:
                falloff = 1.0 - (dist / radius)
                delta = intensity * falloff
                
                if tool_mode == "Height Raise":
                    self.cells[cell_id]["h"] = min(99, int(self.cells[cell_id]["h"] + delta))
                elif tool_mode == "Height Lower":
                    self.cells[cell_id]["h"] = max(1, int(self.cells[cell_id]["h"] - delta))

    def run_hydrology_rivers(self):
        for cell in self.cells:
            cell["fl"] = cell["prec"]
            
        sorted_land = sorted([c for c in self.cells if c["h"] >= 20], key=lambda x: x["h"], reverse=True)
        
        river_id = 1
        for cell in sorted_land:
            neighbors = self.get_neighbors(cell["i"])
            # Must consider all neighbors (including sea) so water can drain into the ocean
            valid_neighbors = [self.cells[n] for n in neighbors]
            if not valid_neighbors:
                continue
            lowest = min(valid_neighbors, key=lambda c: c["h"])
            
            # Flow down to the lowest neighbor
            if lowest["h"] < cell["h"]:
                lowest["fl"] += cell["fl"]
                
                # If enough flux accumulates, it becomes a river
                if cell["fl"] > 35:
                    if cell["r"] == 0:
                        cell["r"] = river_id
                        river_id += 1
                    # Only extend the river ID if the destination is also land
                    if lowest["h"] >= 20:
                        lowest["r"] = cell["r"]

    def _precompute_neighbors(self):
        self._neighbors_map = {i: [] for i in range(self.num_points)}
        for point_pair in self.vor_mesh.ridge_points:
            p1 = int(point_pair[0])
            p2 = int(point_pair[1])
            if p1 < self.num_points and p2 < self.num_points:
                self._neighbors_map[p1].append(p2)
                self._neighbors_map[p2].append(p1)

    def get_neighbors(self, cell_idx):
        return self._neighbors_map.get(cell_idx, [])

    def run_biomes_climate(self, wind_angle_deg=45):
        """
        7-Band Atmospheric & Ocean Surface Current Physics Simulation Layer.
        Calculates wind vectors per band, unloads moisture on rising slopes (Orographic Lift),
        creates Rain Shadows, and simulates wind-driven thermal current deflection.
        """
        # Step 1: Assign Wind Vectors and Base Temperatures by the 7 Horizontal Bands
        for cell in self.cells:
            # Normalize y-axis from 0.0 (North Pole) to 1.0 (South Pole)
            pct_y = cell["y"] / self.height
            
            # Identify 7 strict horizontal climate cells & prevailing winds
            if pct_y < 0.14:   # Band 1: Polar Cap (90°N - 60°N)
                cell["wind_dx"], cell["wind_dy"] = -1.0, 1.0   # ↙️ Polar Easterlies
                base_temp = -15.0
            elif pct_y < 0.28: # Band 2: Subpolar Low (60°N - 45°N)
                cell["wind_dx"], cell["wind_dy"] = 1.0, -1.0   # ↗️ Westerlies
                base_temp = 5.0
            elif pct_y < 0.43: # Band 3: Temperate (45°N - 30°N)
                cell["wind_dx"], cell["wind_dy"] = 1.0, -1.0   # ↗️ Westerlies
                base_temp = 15.0
            elif pct_y < 0.57: # Band 4: Subtropical High / Equatorial (30°N - 15°N)
                cell["wind_dx"], cell["wind_dy"] = -1.0, 1.0   # ↙️ NE Trade Winds
                base_temp = 28.0
            elif pct_y < 0.71: # Band 5: Equatorial Low (15°N - 15°S)
                cell["wind_dx"], cell["wind_dy"] = -1.0, 0.0   # ⬅️ Doldrums
                base_temp = 32.0
            elif pct_y < 0.85: # Band 6: Subtropical Low (15°S - 30°S)
                cell["wind_dx"], cell["wind_dy"] = -1.0, -1.0  # ↖️ SE Trade Winds
                base_temp = 25.0
            else:              # Band 7: Southern Temperate (30°S - 45°S)
                cell["wind_dx"], cell["wind_dy"] = 1.0, -1.0   # ↖️ Westerlies
                base_temp = 12.0

            # Apply baseline temperature and elevation-based lapse rate
            cell["temp"] = base_temp
            if cell["h"] >= 20:
                cell["temp"] -= (cell["h"] - 20) * 0.12 # Mountain alt cooling
            else:
                cell["temp"] -= (20 - cell["h"]) * 0.05 # Abyssal depth cooling

        # Step 2: Simulate Thermal Ocean Currents Deflecting off Continental Barriers
        # We trace water vectors along wind paths to see where they collide with land
        for cell in self.cells:
            cell["current_thermal"] = "neutral"
            if cell["h"] < 20: # Ocean cells only
                # Find downstream cells along wind path
                target_x = cell["x"] + (cell["wind_dx"] * 40)
                target_y = cell["y"] + (cell["wind_dy"] * 40)
                
                # Check for near coastal collisions
                for n_id in self.get_neighbors(cell["i"]):
                    nc = self.cells[n_id]
                    if nc["h"] >= 20: # Hits land barrier -> Deflects Warm/Cold
                        if cell["y"] < self.height * 0.5: # Northern Hemisphere
                            cell["current_thermal"] = "warm" if cell["wind_dx"] > 0 else "cold"
                        else: # Southern Hemisphere
                            cell["current_thermal"] = "cold" if cell["wind_dx"] > 0 else "warm"

        # Apply ocean current temperature anomalies to adjacent coastal land cells
        for cell in self.cells:
            if cell["h"] >= 20:
                for n_id in self.get_neighbors(cell["i"]):
                    nc = self.cells[n_id]
                    if nc["h"] < 20 and nc.get("current_thermal") == "warm":
                        cell["temp"] += 4.0 # Warm current anomaly warming coast
                    elif nc["h"] < 20 and nc.get("current_thermal") == "cold":
                        cell["temp"] -= 5.0 # Cold current anomaly causing coastal deserts

        # Step 3: Orographic Precipitation & Rain Shadow Propagation Loop
        # Sort cells along the vector path of the dominant global winds to run precipitation accumulation
        sorted_cells = sorted(self.cells, key=lambda c: (c["x"] * c.get("wind_dx", 1.0) + c["y"] * c.get("wind_dy", -1.0)))
        
        # Track simulated saturated moisture levels across grid edges
        moisture_map = {c["i"]: 1.0 for c in self.cells}
        
        for cell in sorted_cells:
            c_idx = cell["i"]
            air_moisture = moisture_map[c_idx]

            if cell["h"] < 20:
                # Regain water saturation over open ocean paths
                air_moisture = min(1.0, air_moisture + 0.25)
                cell["prec"] = int(air_moisture * 80)
            else:
                # Evaluate upwind height compared to neighbors to calculate elevation slopes
                neighbors = self.get_neighbors(c_idx)
                upwind_nodes = [self.cells[n] for n in neighbors if (self.cells[n]["x"] * cell["wind_dx"] + self.cells[n]["y"] * cell["wind_dy"]) < (cell["x"] * cell["wind_dx"] + cell["y"] * cell["wind_dy"])]
                
                if upwind_nodes:
                    lowest_upwind = min(upwind_nodes, key=lambda x: x["h"])
                    slope = cell["h"] - lowest_upwind["h"]
                    
                    if slope > 5:
                        # Wind hits a rising slope (Orographic Lift) -> Heavy Rain Dump
                        dump = air_moisture * (slope / 100.0) * 2.5
                        cell["prec"] = int(dump * 120)
                        air_moisture = max(0.05, air_moisture - dump)
                    else:
                        # Downward slope or flat ground -> Rain Shadow Effect
                        cell["prec"] = int(air_moisture * 15)
                        air_moisture = max(0.02, air_moisture - 0.02)
                else:
                    cell["prec"] = int(air_moisture * 30)

            # Pass the modified air mass downstream to downwind neighbors
            for n_id in self.get_neighbors(c_idx):
                if (self.cells[n_id]["x"] * cell["wind_dx"] + self.cells[n_id]["y"] * cell["wind_dy"]) > (cell["x"] * cell["wind_dx"] + cell["y"] * cell["wind_dy"]):
                    moisture_map[n_id] = air_moisture

        # Recalculate the final Whittaker biomes matrix with our accurate physics arrays
        for cell in self.cells:
            self._assign_whittaker_biomes_for_cell(cell)
    def _assign_whittaker_biomes_for_cell(self, cell):
        h = cell["h"]
        t = cell["temp"]
        p = cell["prec"]
        
        if h < 20:
            depth = 20 - h
            cell["is_aquatic"] = True
            if depth > 15:
                cell["biome"] = "Abyssal Trench (Desert)"
            elif depth > 10:
                cell["biome"] = "Coral Forest (Rainforest)"
            elif p > 40:
                cell["biome"] = "Kelp Meadows (Grassland)"
            else:
                cell["biome"] = "Benthic Shelf (Savanna)"
            return
            
        if h > 80:
            cell["biome"] = "Montane / Glacier"
        elif t < -5:
            cell["biome"] = "Ice Sheet / Perpetual Frost"
        elif t < 2:
            if p < 10:   cell["biome"] = "Cold Desert"
            else:        cell["biome"] = "Tundra"
        elif t < 10:
            if p < 20:   cell["biome"] = "Subarctic Dry Steppe"
            elif p < 60:  cell["biome"] = "Taiga / Boreal Forest"
            else:        cell["biome"] = "Temperate Rainforest"
        elif t < 20:
            if p < 15:   cell["biome"] = "Cold Desert"
            elif p < 35:  cell["biome"] = "Grassland / Prairie"
            elif p < 75:  cell["biome"] = "Temperate Deciduous Forest"
            else:        cell["biome"] = "Maritime Rainforest"
        else:
            if p < 15:   cell["biome"] = "Hot Desert"
            elif p < 45:  cell["biome"] = "Tropical Savanna"
            elif p < 80:  cell["biome"] = "Seasonal Tropical Forest"
            else:        cell["biome"] = "Equatorial Rainforest"

    def run_cultures_generation(self):
        self.cultures = []
        culture_names = ["Ostraka Mammalian", "Ostraka Reptilian", "Ostraka Avian", "Ostraka Insectoid", "Ostraka Aquatic", "Ostraka Botanical"]
        env_types = ["Terrestrial", "Terrestrial", "Terrestrial", "Terrestrial", "Aquatic", "Terrestrial"]
        for idx, name in enumerate(culture_names):
            culture_id = idx + 1
            self.cultures.append({
                "id": culture_id,
                "name": name,
                "code": name.split(" ")[1][:3].upper(),
                "is_aquatic": True if "Aquatic" in name else False,
                "env_type": env_types[idx]
            })
            
        pq = []
        for cell in self.cells:
            cell["culture"] = 0
            
        for idx, cult in enumerate(self.cultures):
            seed_cell_id = idx * (len(self.cells) // len(self.cultures))
            self.cells[seed_cell_id]["culture"] = cult["id"]
            heapq.heappush(pq, (0.0, seed_cell_id, cult["id"], cult["env_type"]))
            
        while pq:
            accumulated_friction, current_id, culture_id, env_type = heapq.heappop(pq)
            neighbors = self.get_neighbors(current_id)
            for n_id in neighbors:
                neighbor_cell = self.cells[n_id]
                if neighbor_cell["culture"] != 0:
                    continue
                    
                elevation = neighbor_cell["h"]
                if elevation >= 20:
                    if env_type == "Aquatic":
                        friction = 500.0
                    else:
                        friction = 10.0
                else:
                    if env_type == "Terrestrial":
                        friction = 150.0
                    elif elevation < 10:
                        friction = 5.0
                    else:
                        friction = 20.0
                        
                total_friction = accumulated_friction + friction
                if total_friction < 800.0:
                    neighbor_cell["culture"] = culture_id
                    heapq.heappush(pq, (total_friction, n_id, culture_id, env_type))

    def run_states_expansion(self, num_states=6):
        self.states = []
        potential_capitals = sorted(self.cells, key=lambda c: c["fl"], reverse=True)
        
        pq = []
        placed = 0
        for cap in potential_capitals:
            state_id = len(self.states) + 1
            cap["state"] = state_id
            
            is_cap_aquatic = cap["h"] < 20
            state_type = "Aquatic" if is_cap_aquatic else "Terrestrial"
            
            # Generate state name from localized culture namesbase config
            culture_id = cap["culture"]
            c_name = self.cultures[culture_id - 1]["name"] if culture_id > 0 else "Ostraka Mammalian"
            name = self.name_gen.generate_name(c_name)
            
            self.states.append({
                "id": state_id,
                "capital_cell": cap["i"],
                "color": f"#{random.randint(50,255):02x}{random.randint(50,255):02x}{random.randint(50,255):02x}",
                "expansionism": random.uniform(0.5, 2.5),
                "is_aquatic": is_cap_aquatic,
                "type": state_type,
                "max_influence": 50.0,
                "area": 0,
                "name": f"Empire of {name}",
                "diplomacy": {}
            })
            
            heapq.heappush(pq, (0.0, cap["i"], state_id, state_type))
            placed += 1
            if placed >= num_states:
                break
            
        while pq:
            accumulated_cost, current_id, state_id, state_type = heapq.heappop(pq)
            neighbors = self.get_neighbors(current_id)
            
            for n_id in neighbors:
                neighbor_cell = self.cells[n_id]
                if neighbor_cell["state"] != 0:
                    continue
                    
                elevation = neighbor_cell["h"]
                if elevation >= 20:
                    if state_type == "Aquatic":
                        friction = 9999.0
                    else:
                        friction = 10.0
                else:
                    if state_type == "Terrestrial":
                        friction = 120.0
                    elif elevation < 10:
                        friction = 5.0
                    else:
                        friction = 15.0
                        
                total_cost = accumulated_cost + friction
                if total_cost < self.states[state_id - 1]["max_influence"]:
                    neighbor_cell["state"] = state_id
                    heapq.heappush(pq, (total_cost, n_id, state_id, state_type))

    def slice_state_provinces(self, provinces_per_state=3):
        province_id_counter = 1
        self.provinces_pool = {}
        
        for cell in self.cells:
            cell["province"] = 0

        for state in self.states:
            state_id = state["id"]
            state_cells = [c for c in self.cells if c["state"] == state_id]
            if not state_cells:
                continue
                
            candidate_seeds = [c for c in state_cells if c["i"] != state["capital_cell"]]
            if len(candidate_seeds) < provinces_per_state:
                candidate_seeds = state_cells
                
            province_seeds = random.sample(candidate_seeds, min(provinces_per_state, len(candidate_seeds)))
            
            queue = []
            for seed in province_seeds:
                pid = province_id_counter
                cell_id = seed["i"]
                self.cells[cell_id]["province"] = pid
                
                hex_str = state["color"].lstrip('#')
                r, g, b = tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
                r = max(0, min(255, r + random.randint(-35, 35)))
                g = max(0, min(255, g + random.randint(-35, 35)))
                b = max(0, min(255, b + random.randint(-35, 35)))
                
                self.provinces_pool[pid] = {
                    "id": pid,
                    "state_id": state_id,
                    "color": f"#{r:02x}{g:02x}{b:02x}"
                }
                queue.append((cell_id, pid))
                province_id_counter += 1
                
            while queue:
                curr_id, curr_pid = queue.pop(0)
                neighbors = self.get_neighbors(curr_id)
                for n_id in neighbors:
                    neighbor_cell = self.cells[n_id]
                    if neighbor_cell["state"] == state_id and neighbor_cell["province"] == 0:
                        neighbor_cell["province"] = curr_pid
                        queue.append((n_id, curr_pid))

    def run_diplomacy_matrix_engine(self):
        for st in self.states:
            st["diplomacy"] = {}
            st["border_friction"] = {}

        for cell in self.cells:
            sid = cell["state"]
            if sid == 0: continue
            
            for n_id in self.get_neighbors(cell["i"]):
                nsid = self.cells[n_id]["state"]
                if nsid != 0 and nsid != sid:
                    self.states[sid - 1]["border_friction"][nsid] = \
                        self.states[sid - 1]["border_friction"].get(nsid, 0) + 1

        for s1 in self.states:
            for s2 in self.states:
                if s1["id"] == s2["id"]: continue
                
                rel_score = 50.0
                shared_edges = s1["border_friction"].get(s2["id"], 0)
                if shared_edges > 0:
                    rel_score -= (shared_edges * 3.0) * s1["expansionism"]
                else:
                    rel_score += 15.0
                    
                s1_cap_cult = self.cells[s1["capital_cell"]]["culture"]
                s2_cap_cult = self.cells[s2["capital_cell"]]["culture"]
                if s1_cap_cult == s2_cap_cult:
                    rel_score += 20.0
                    
                if rel_score < 20.0:    status = "War"
                elif rel_score < 45.0:  status = "Suspicion"
                elif rel_score < 75.0:  status = "Peace"
                else:                  status = "Alliance"
                
                s1["diplomacy"][s2["id"]] = {
                    "score": round(rel_score, 1),
                    "status": status
                }

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
                cell["religion"] = 4
            else:
                cell["religion"] = (cell["i"] % 3) + 1

    def run_burgs_generation(self, max_burgs=15):
        self.burgs = []
        sorted_candidates = sorted(self.cells, key=lambda c: (c["fl"] if c["r"] > 0 else 0) + (20 - c["h"] if c["h"] < 20 else c["h"]), reverse=True)
        
        placed = 0
        for cell in sorted_candidates:
            if cell["burg"] == 0:
                burg_id = len(self.burgs) + 1
                cell["burg"] = burg_id
                
                culture_id = cell["culture"]
                profile_key = "Ostraka Mammalian"
                if culture_id > 0 and culture_id <= len(self.cultures):
                    profile_key = self.cultures[culture_id - 1]["name"]
                    
                name = self.name_gen.generate_name(profile_key)
                
                self.burgs.append({
                    "id": burg_id,
                    "cell_idx": cell["i"],
                    "name": name,
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
            
            path = self.find_astar_path(b1["cell_idx"], b2["cell_idx"])
            if path:
                self.roads.append({
                    "id": idx + 1,
                    "from_burg": b1["id"],
                    "to_burg": b2["id"],
                    "path": path,
                    "type": "Abyssal Conduit" if self.cells[b1["cell_idx"]]["h"] < 20 else "Highroad"
                })

    def find_astar_path(self, start_idx, end_idx):
        start_cell = self.cells[start_idx]
        end_cell = self.cells[end_idx]
        
        def heuristic(c1, c2):
            return math.sqrt((c1["x"] - c2["x"])**2 + (c1["y"] - c2["y"])**2)
            
        pq = []
        heapq.heappush(pq, (heuristic(start_cell, end_cell), start_idx, [start_idx]))
        g_scores = {start_idx: 0.0}
        visited = set()
        
        while pq:
            _, current, path = heapq.heappop(pq)
            
            if current == end_idx:
                return path
                
            if current in visited: continue
            visited.add(current)
            
            curr_cell = self.cells[current]
            for n_id in self.get_neighbors(current):
                if n_id in visited: continue
                n_cell = self.cells[n_id]
                
                dist_cost = heuristic(curr_cell, n_cell)
                slope_penalty = abs(n_cell["h"] - curr_cell["h"]) * 2.0
                
                medium_penalty = 0.0
                if (curr_cell["h"] >= 20 and n_cell["h"] < 20) or (curr_cell["h"] < 20 and n_cell["h"] >= 20):
                    medium_penalty = 50.0 
                    
                tentative_g = g_scores[current] + dist_cost + slope_penalty + medium_penalty
                
                if tentative_g < g_scores.get(n_id, float('inf')):
                    g_scores[n_id] = tentative_g
                    f_score = tentative_g + heuristic(n_cell, end_cell)
                    heapq.heappush(pq, (f_score, n_id, path + [n_id]))
                    
        return []

    def run_trade_and_market_simulation(self):
        for burg in self.burgs:
            burg["market_demand"] = {}
            burg["trade_income"] = 0.0
            cell = self.cells[burg["cell_idx"]]
            burg["produces"] = cell["good"]

        for road in self.roads:
            b1 = next((b for b in self.burgs if b["id"] == road["from_burg"]), None)
            b2 = next((b for b in self.burgs if b["id"] == road["to_burg"]), None)
            
            if b1 and b2:
                volume = (b1["population"] * b2["population"]) / 10.0
                road["trade_volume"] = round(volume, 1)
                
                if b1["produces"] != b2["produces"]:
                    b1["market_demand"][b2["produces"]] = round(volume * 1.5, 1)
                    b2["market_demand"][b1["produces"]] = round(volume * 1.5, 1)

    def run_military_generator(self):
        self.military_regiments = []
        reg_id = 1
        for st in self.states:
            cap_cell = self.cells[state["capital_cell"] if "capital_cell" in (state := st) else 0]
            self.military_regiments.append({
                "id": reg_id,
                "state_id": st["id"],
                "name": f"Royal Guards of {st['name']}",
                "cell_idx": cap_cell["i"],
                "total_troops": 1200
            })
            reg_id += 1

    def run_production_goods(self):
        goods_manifest = {
            1: "Grain", 2: "Timber", 3: "Spices", 4: "Iron Ore", 
            5: "Bioluminescent Kelp", 6: "Precious Metals", 7: "Abyssal Pearls"
        }
        
        for cell in self.cells:
            h = cell["h"]
            biome = cell["biome"]
            
            if h < 20:
                cell["good"] = goods_manifest[7] if h < 5 else goods_manifest[5]
            elif h > 75:
                cell["good"] = goods_manifest[6] if h > 85 else goods_manifest[4]
            elif biome == "Tropical Rainforest":
                cell["good"] = goods_manifest[3]
            elif biome == "Hot Desert":
                cell["good"] = "Salt"
            else:
                cell["good"] = goods_manifest[1] if cell["fl"] > 20 else goods_manifest[2]

    def sink_generated_world_to_db(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # New tables for full world export
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS biomes (
                cell_id INTEGER PRIMARY KEY,
                biome TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS production_goods (
                cell_id INTEGER PRIMARY KEY,
                good TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relief_icons (
                cell_id INTEGER PRIMARY KEY,
                icon_type TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS markers (
                cell_id INTEGER PRIMARY KEY,
                label TEXT,
                data TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emblems (
                state_id INTEGER PRIMARY KEY,
                svg BLOB
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ui_overlays (
                layer TEXT PRIMARY KEY,
                enabled INTEGER
            )
        """)

        try:
            cursor.execute("DELETE FROM magic_layers")
            cursor.execute("DELETE FROM cell_neighbors")
            cursor.execute("DELETE FROM cells")
            cursor.execute("DELETE FROM settlements")
            cursor.execute("DELETE FROM factions")
            
            for st in self.states:
                cursor.execute("""
                    INSERT INTO factions (id, name, color, treasury, tech_level)
                    VALUES (?, ?, ?, 0.0, 1)
                """, (st["id"], st["name"], st["color"]))
                
            for cell in self.cells:
                cursor.execute("""
                    INSERT INTO cells (id, centroid_x, centroid_y, elevation, moisture, temperature, state_id, province_id, culture_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cell["i"], cell["x"], cell["y"], cell["h"], cell["prec"], cell["temp"],
                    cell["state"] if cell["state"] > 0 else None,
                    cell["province"] if cell["province"] > 0 else None,
                    cell["culture"] if cell["culture"] > 0 else None
                ))
                
                for n_id in self.get_neighbors(cell["i"]):
                    cursor.execute("""
                        INSERT OR IGNORE INTO cell_neighbors (cell_id, neighbor_id)
                        VALUES (?, ?)
                    """, (cell["i"], n_id))
                    
            # Insert biomes, goods, relief icons, markers per cell
            for cell in self.cells:
                # Biome
                cursor.execute("INSERT OR REPLACE INTO biomes (cell_id, biome) VALUES (?, ?)", (cell["i"], cell.get("biome", "")))
                # Production good
                cursor.execute("INSERT OR REPLACE INTO production_goods (cell_id, good) VALUES (?, ?)", (cell["i"], cell.get("good", "")))
                # Relief icons (mountain or forest)
                icon_type = None
                if cell.get("h", 0) >= 70:
                    icon_type = "mountain"
                elif "Forest" in cell.get("biome", "") or "Taiga" in cell.get("biome", ""):
                    icon_type = "forest"
                if icon_type:
                    cursor.execute("INSERT OR REPLACE INTO relief_icons (cell_id, icon_type) VALUES (?, ?)", (cell["i"], icon_type))
                # Markers – placeholder for future POIs (none by default)
                # (If your engine stores markers elsewhere, replace this block accordingly)
                pass
            for burg in self.burgs:
                cursor.execute("""
                    INSERT INTO settlements (name, q, r, population, faction_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (burg["name"], burg["cell_idx"], 0, burg["population"] * 100, 1))
                
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
