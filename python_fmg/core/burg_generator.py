import math
import random

from .namebases_data import NAMEBASES
import re

class MarkovNameGenerator:
    def __init__(self):
        self.chains = {}

    def is_vowel(self, char):
        return char.lower() in 'aeiouy'

    def calculate_chain(self, names_list):
        chain = {}
        available_names = [n.strip().lower() for n in names_list.split(",")]

        for name in available_names:
            basic = not bool(re.search(r'[^\x20-\x7e]', name))
            i = -1
            syllable = ""
            while i < len(name):
                prev = name[i] if i >= 0 else ""
                syllable = ""
                v = 0
                c = i + 1
                while c < len(name) and len(syllable) < 5:
                    that = name[c]
                    next_c = name[c + 1] if c + 1 < len(name) else ""
                    syllable += that
                    
                    if syllable == " " or syllable == "-": break
                    if not next_c or next_c == " " or next_c == "-": break
                    
                    if self.is_vowel(that):
                        v = 1
                        
                    if that == "y" and next_c == "e": pass
                    elif basic:
                        if (that == "o" and next_c == "o") or \
                           (that == "e" and next_c == "e") or \
                           (that == "a" and next_c == "e") or \
                           (that == "c" and next_c == "h"):
                            pass
                        elif self.is_vowel(that) == self.is_vowel(next_c): break
                        elif v and c + 2 < len(name) and self.is_vowel(name[c + 2]): break
                    else:
                        if self.is_vowel(that) == self.is_vowel(next_c): break
                        elif v and c + 2 < len(name) and self.is_vowel(name[c + 2]): break
                        
                    c += 1
                
                if prev not in chain:
                    chain[prev] = []
                chain[prev].append(syllable)
                i += max(1, len(syllable))
                
        return chain

    def get_base(self, base_idx):
        if base_idx < 0 or base_idx >= len(NAMEBASES):
            base_idx = 0
            
        if base_idx not in self.chains:
            self.chains[base_idx] = self.calculate_chain(NAMEBASES[base_idx]["b"])
            
        data = self.chains[base_idx]
        base_def = NAMEBASES[base_idx]
        min_len = base_def.get("min", 5)
        max_len = base_def.get("max", 12)
        dupl = base_def.get("d", "")
        
        v = data.get("", [])
        if not v:
            return "Error"
            
        cur = random.choice(v) if v else ""
        w = ""
        
        for _ in range(20):
            if cur == "":
                if len(w) < min_len:
                    cur = ""
                    w = ""
                    v = data.get("", [])
                else:
                    break
            else:
                if len(w) + len(cur) > max_len:
                    if len(w) < min_len:
                        w += cur
                    break
                else:
                    last_char = cur[-1] if cur else ""
                    v = data.get(last_char, data.get("", []))
            
            w += cur
            cur = random.choice(v) if v else ""
            
        if not w: return "Error"
        
        # Parse final name
        l = w[-1]
        if l in ["'", " ", "-"]:
            w = w[:-1]
            
        name = ""
        for i, c in enumerate(w):
            if i + 1 < len(w) and c == w[i + 1] and c not in dupl: continue
            if not name: 
                name += c.upper()
                continue
            if name[-1] == "-" and c == " ": continue
            if name[-1] == " ":
                name += c.upper()
                continue
            if name[-1] == "-":
                name += c.upper()
                continue
            if c == "a" and i + 1 < len(w) and w[i + 1] == "e": continue
            if i + 2 < len(w) and c == w[i + 1] and c == w[i + 2]: continue
            name += c
            
        if len(name) < 2:
            return random.choice(base_def["b"].split(","))
            
        return name

    def generate_name(self, profile_key=None):
        # Default to English (1) if no valid int passed
        try:
            base_idx = int(profile_key) if profile_key is not None else 1
        except:
            base_idx = 1
            
        return self.get_base(base_idx)

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
