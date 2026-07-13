import os

filepath = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\core\ai_worker.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace dissection_schema
old_schema = """        dissection_schema = {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "enum": ["Characters", "Factions", "Locations", "Cultures", "Religions", "General"]
                },
                "faction": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "gov_type": {"type": "STRING"},
                        "magic_stance": {"type": "STRING"},
                        "domain_type": {"type": "STRING"}
                    }
                },
                "religion": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "religion_type": {"type": "STRING"},
                        "supreme_deity": {"type": "STRING"}
                    }
                },
                "settlement": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "population_k": {"type": "NUMBER"}
                    }
                }
            },
            "required": ["category"]
        }"""

new_schema = """        dissection_schema = {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "enum": ["Characters", "Factions", "Locations", "Cultures", "Religions", "General"]
                },
                "faction": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "gov_type": {"type": "STRING"},
                        "magic_stance": {"type": "STRING"},
                        "domain_type": {"type": "STRING"}
                    }
                },
                "religion": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "religion_type": {"type": "STRING"},
                        "supreme_deity": {"type": "STRING"}
                    }
                },
                "settlement": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "population_k": {"type": "NUMBER"}
                    }
                },
                "actor": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "faction_name": {"type": "STRING"},
                        "role": {"type": "STRING"}
                    }
                },
                "faction_economic_status": {
                    "type": "OBJECT",
                    "properties": {
                        "faction_name": {"type": "STRING"},
                        "good_name": {"type": "STRING"},
                        "status": {"type": "STRING", "enum": ["Surplus", "Deficit"]},
                        "urgency_multiplier": {"type": "NUMBER"}
                    }
                },
                "diplomacy_tension": {
                    "type": "OBJECT",
                    "properties": {
                        "faction_a": {"type": "STRING"},
                        "faction_b": {"type": "STRING"},
                        "diplomacy_score": {"type": "INTEGER"},
                        "treaty_status": {"type": "STRING"}
                    }
                },
                "atomic_facts": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "subject": {"type": "STRING"},
                            "relationship": {"type": "STRING"},
                            "target": {"type": "STRING"},
                            "context": {"type": "STRING"}
                        }
                    }
                }
            },
            "required": ["category"]
        }"""

content = content.replace(old_schema, new_schema)

# 2. Add SQL Insertion Logic for the new fields
# I will find the block:
#                     if "settlement" in dissected_data and dissected_data["settlement"].get("name"):
#                         s = dissected_data["settlement"]
#                         cursor.execute(\"\"\"
#                             INSERT INTO settlements (name, population, cell_idx, associated_note_id)
#                             VALUES (?, ?, ?, ?)
#                         \"\"\", (s["name"], s.get("population_k", 10.0), random.randint(100, 900), note_id))
old_insert = """                    if "settlement" in dissected_data and dissected_data["settlement"].get("name"):
                        s = dissected_data["settlement"]
                        cursor.execute(\"\"\"
                            INSERT INTO settlements (name, population, cell_idx, associated_note_id)
                            VALUES (?, ?, ?, ?)
                        \"\"\", (s["name"], s.get("population_k", 10.0), random.randint(100, 900), note_id))"""

new_insert = """                    if "settlement" in dissected_data and dissected_data["settlement"].get("name"):
                        s = dissected_data["settlement"]
                        cursor.execute(\"\"\"
                            INSERT INTO settlements (name, population, cell_idx, associated_note_id)
                            VALUES (?, ?, ?, ?)
                        \"\"\", (s["name"], s.get("population_k", 10.0), random.randint(100, 900), note_id))

                    if "actor" in dissected_data and dissected_data["actor"].get("name"):
                        a = dissected_data["actor"]
                        # Get faction id if possible
                        cursor.execute("SELECT id FROM factions WHERE name=?", (a.get("faction_name"),))
                        f_row = cursor.fetchone()
                        f_id = f_row[0] if f_row else None
                        cursor.execute(\"\"\"
                            INSERT INTO actors (name, faction_id, current_cell_idx, is_alive, role)
                            VALUES (?, ?, ?, 1, ?)
                        \"\"\", (a["name"], f_id, random.randint(100, 900), a.get("role")))

                    if "faction_economic_status" in dissected_data and dissected_data["faction_economic_status"].get("faction_name"):
                        e = dissected_data["faction_economic_status"]
                        cursor.execute("SELECT id FROM factions WHERE name=?", (e.get("faction_name"),))
                        f_row = cursor.fetchone()
                        f_id = f_row[0] if f_row else None
                        if f_id:
                            cursor.execute(\"\"\"
                                INSERT INTO faction_economics (faction_id, good_name, status, urgency_multiplier)
                                VALUES (?, ?, ?, ?)
                            \"\"\", (f_id, e.get("good_name"), e.get("status"), e.get("urgency_multiplier", 1.0)))

                    if "diplomacy_tension" in dissected_data and dissected_data["diplomacy_tension"].get("faction_a") and dissected_data["diplomacy_tension"].get("faction_b"):
                        d = dissected_data["diplomacy_tension"]
                        cursor.execute("SELECT id FROM factions WHERE name=?", (d.get("faction_a"),))
                        fa_row = cursor.fetchone()
                        cursor.execute("SELECT id FROM factions WHERE name=?", (d.get("faction_b"),))
                        fb_row = cursor.fetchone()
                        if fa_row and fb_row:
                            try:
                                cursor.execute(\"\"\"
                                    INSERT INTO faction_relations (faction_a_id, faction_b_id, diplomacy_score, treaty_status)
                                    VALUES (?, ?, ?, ?)
                                \"\"\", (fa_row[0], fb_row[0], d.get("diplomacy_score", 0), d.get("treaty_status", "Neutral")))
                            except sqlite3.IntegrityError:
                                pass # Unique constraint failed, relation exists

                    if "atomic_facts" in dissected_data and isinstance(dissected_data["atomic_facts"], list):
                        for fact in dissected_data["atomic_facts"]:
                            if fact.get("subject") and fact.get("relationship") and fact.get("target"):
                                cursor.execute(\"\"\"
                                    INSERT INTO atomic_facts (subject, relationship, target, context, associated_note_id)
                                    VALUES (?, ?, ?, ?, ?)
                                \"\"\", (fact.get("subject"), fact.get("relationship"), fact.get("target"), fact.get("context", ""), note_id))"""

content = content.replace(old_insert, new_insert)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("ai_worker.py schema and SQL insert logic updated.")
