import math
import random

class MarkovNameGenerator:
    def __init__(self):
        # Phonetics profile mappings expanded to mimic JS FMG templates
        self.language_profiles = {
            "Terrestrial_Highland": {
                "syllables": ["thran", "dar", "krag", "gol", "rum", "vath", "marn", "khaz", "grom", "duhr"],
                "min_len": 2, "max_len": 3, "spacer": ""
            },
            "Aquatic_Deep_Folk": {
                "syllables": ["tlal", "cthul", "vyr", "nax", "zith", "shur", "aqu", "slith", "glub", "murex"],
                "min_len": 2, "max_len": 4, "spacer": "'"
            },
            "Magic_Ley_Elves": {
                "syllables": ["ael", "fae", "ryn", "eth", "val", "ith", "morn", "shala", "lor", "tari"],
                "min_len": 3, "max_len": 5, "spacer": ""
            }
        }

    def generate_name(self, profile_key):
        profile = self.language_profiles.get(profile_key, self.language_profiles["Terrestrial_Highland"])
        length = random.randint(profile["min_len"], profile["max_len"])
        chosen_syllables = random.sample(profile["syllables"], length)
        raw_name = profile["spacer"].join(chosen_syllables)
        return raw_name.capitalize()

class BurgGenerator:
    """
    Procedural Settlement Block & Road network generator mapping street grids 
    to cell terrains based on population sizes (FMG equivalent burg map generator).
    """
    def __init__(self):
        pass
        
    def generate_settlement_layout(self, cell_idx, pop_size, cell_elevation):
        # Procedurally build block vectors and local streets
        random.seed(cell_idx)
        num_blocks = int(pop_size * 2)
        blocks = []
        streets = []
        
        # Settle central plaza
        center_x, center_y = 100, 100
        plaza_radius = 15
        
        # Settle arterial roads outward
        num_roads = 4 if cell_elevation >= 20 else 2 # Less roads on coastal/wharf grids
        for angle_idx in range(num_roads):
            angle = (angle_idx / num_roads) * 2.0 * math.pi
            rx = center_x + math.cos(angle) * 80
            ry = center_y + math.sin(angle) * 80
            streets.append(((center_x, center_y), (rx, ry)))
            
            # Place houses / block vectors along these roads
            for dist in [30, 50, 70]:
                bx = center_x + math.cos(angle) * dist + random.uniform(-10, 10)
                by = center_y + math.sin(angle) * dist + random.uniform(-10, 10)
                blocks.append((bx - 8, by - 8, 16, 16))
                
        return {
            "center": (center_x, center_y),
            "plaza_radius": plaza_radius,
            "streets": streets,
            "blocks": blocks
        }
