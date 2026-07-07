import random

class EmblemGenerator:
    """
    Python implementation of FMG's draw-emblems.ts / modules/emblem/generator.ts.
    Generates procedural shields, divisions, ordinaries, and charges for states and cultures.
    """
    def __init__(self):
        self.tinctures = {
            "metals": ["or", "argent"],
            "colors": ["gules", "azure", "sable", "vert", "purpure"],
            "rare": ["tenne", "sanguine"]
        }
        
        self.divisions = [
            "perFess", "perPale", "perBend", "perBendSinister", 
            "perChevron", "perChevronReversed", "perCross", "perSaltire"
        ]
        
        self.ordinaries = [
            "fess", "pale", "bend", "bendSinister", "chief", "bar", 
            "cross", "saltire", "chevron", "chevronReversed"
        ]
        
        self.charges = [
            "lionRampant", "eagleDisplayed", "boarRampant", "stagTrippant",
            "dragonRampant", "crossRampant", "sword", "crown", "tower"
        ]

    def generate(self, name_seed=None):
        if name_seed:
            random.seed(name_seed)
            
        t1 = random.choice(self.tinctures["metals"] + self.tinctures["colors"])
        t2 = random.choice(self.tinctures["metals"] if t1 in self.tinctures["colors"] else self.tinctures["colors"])
        
        coa = {
            "t1": t1,
            "shield": "heater",
            "division": None,
            "ordinaries": [],
            "charges": []
        }
        
        # 30% chance of division
        if random.random() < 0.3:
            coa["division"] = {
                "division": random.choice(self.divisions),
                "t": t2
            }
            
        # 40% chance of ordinary
        if random.random() < 0.4:
            t3 = random.choice(self.tinctures["metals"] if t1 in self.tinctures["colors"] else self.tinctures["colors"])
            coa["ordinaries"].append({
                "ordinary": random.choice(self.ordinaries),
                "t": t3
            })
            
        # 60% chance of charge
        if random.random() < 0.6:
            t4 = random.choice(self.tinctures["metals"] if t1 in self.tinctures["colors"] else self.tinctures["colors"])
            coa["charges"].append({
                "charge": random.choice(self.charges),
                "t": t4,
                "size": 1.0
            })
            
        return coa

    def render_to_svg(self, coa):
        # Returns simple path string and styles representing the crest
        shield_paths = {
            "heater": "M 0 0 L 200 0 L 200 100 Q 200 170 100 200 Q 0 170 0 100 Z"
        }
        
        color_map = {
            "or": "#eab308", "argent": "#cbd5e1",
            "gules": "#ef4444", "azure": "#3b82f6",
            "sable": "#18181b", "vert": "#10b981",
            "purpure": "#8b5cf6"
        }
        
        p = shield_paths.get(coa["shield"], shield_paths["heater"])
        c1 = color_map.get(coa["t1"], "#cbd5e1")
        
        svg = f'<svg width="100" height="100" viewBox="0 0 200 200">'
        svg += f'<path d="{p}" fill="{c1}" stroke="#000000" stroke-width="4"/>'
        
        if coa["division"]:
            c2 = color_map.get(coa["division"]["t"], "#3b82f6")
            div = coa["division"]["division"]
            if div == "perPale":
                svg += f'<path d="M 100 0 L 200 0 L 200 100 Q 200 170 100 200 Z" fill="{c2}"/>'
            elif div == "perFess":
                svg += f'<path d="M 0 100 L 200 100 L 200 100 Q 200 170 100 200 Q 0 170 0 100 Z" fill="{c2}"/>'
                
        for ord_info in coa["ordinaries"]:
            c3 = color_map.get(ord_info["t"], "#ef4444")
            if ord_info["ordinary"] == "fess":
                svg += f'<rect x="0" y="75" width="200" height="50" fill="{c3}"/>'
            elif ord_info["ordinary"] == "pale":
                svg += f'<rect x="75" y="0" width="50" height="200" fill="{c3}"/>'
                
        svg += '</svg>'
        return svg
