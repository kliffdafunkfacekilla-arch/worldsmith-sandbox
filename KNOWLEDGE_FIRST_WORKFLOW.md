🌌 LORDSMITH STUDIO: KNOWLEDGE-FIRST WORLD SYNTHESIS WORKFLOW
This document establishes the official workflow, logical stages, and architectural data pipeline for Lordsmith Studio.
Instead of generating a random terrain mesh on startup, this workflow treats your written lore notes as the absolute source of truth. No map is generated until your notes are carefully dissected, structured into an interconnected knowledge base, and converted into spatial and cultural layout rules.
🔄 THE 3-STAGE KNOWLEDGE-FIRST PIPELINE
 ┌───────────────────────────┐      ┌───────────────────────────┐      ┌───────────────────────────┐
 │ STAGE 1: INGEST & PARSE   │ ───> │ STAGE 2: KNOWLEDGE BASE   │ ───> │ STAGE 3: SYNTHESIZE MAP   │
 └───────────────────────────┘      └───────────────────────────┘      └───────────────────────────┘
   - Load raw note folder             - Extract entities to SQL          - Run layout constraint solver
   - Extract entities/relations       - Verify relational consistency    - Generate Voronoi mesh
   - Generate structured metadata     - Display data spreadsheets        - Seed layers from prose


📄 STAGE 1: THE INGESTION & DISSECTION ENGINE
When a user imports an unstructured directory of text files, the system goes into an Ingestion and Dissection Standby State. It does not boot up the map. Instead, it reads through the markdown and text files, running individual extraction models to parse unstructured paragraphs into clear, semantic metadata.
🔍 How the AI Dissects Unstructured Notes
Let's trace what happens when the engine parses a raw paragraph:
User's Raw Prose Note:
"The Obsidian Citadel is the ancient, volcanic capital of the Vulfurn Empire, situated in the frozen northern wastes of North Reach. It is surrounded by Boreal Elves who worship the Eternal Dawn. The citadel has a standing garrison of 1,500 Elite Shields to protect the massive iron ore deposits mined in the deep obsidian chasms."
The AI Dissection & Entity Extraction Output:
The AI parses this paragraph into a clean, structured JSON schema mapping directly to your relational database tables:
{
  "burg": {
    "name": "Obsidian Citadel",
    "population": 15,
    "role": "Sovereign Capital",
    "geographical_indicators": ["Volcanic Area", "Frozen Wastes", "Chasms"]
  },
  "faction": {
    "name": "Vulfurn Empire",
    "expansionism": 1.2,
    "primary_color": "#ef4444"
  },
  "province": {
    "name": "North Reach",
    "climate": "Subpolar / Frozen"
  },
  "culture": {
    "name": "Boreal Elves",
    "language_code": "BE"
  },
  "religion": {
    "name": "Eternal Dawn",
    "supreme_deity": "Solis"
  },
  "commodity": {
    "cell_good": "Iron Ore",
    "local_valuation": 2.5
  },
  "military": {
    "troops": 1500,
    "unit_name": "Elite Shields"
  },
  "spatial_constraints": [
    {"entity": "Obsidian Citadel", "relation": "inside", "target": "North Reach"},
    {"entity": "Boreal Elves", "relation": "surrounds", "target": "Obsidian Citadel"}
  ]
}


🗄️ STAGE 2: THE COORDINATED KNOWLEDGE BASE
Once parsed, this structured data is committed to your SQLite database. The user interface displays these entries inside your interactive Spreadsheet Dashboards (left panel).
At this stage, you have a complete, highly structured catalog of your world without any spatial coordinates yet. This gives the local AI a unified knowledge base to query:
                                LORDSMITH DATABASE NODES
                                
      [Sovereign States]          [Ethno-Cultures]               [Religions]
        - Vulfurn Empire            - Boreal Elves             - Eternal Dawn
               ▲                           ▲                          ▲
               │                           │                          │
               └───────────────┬───────────┴──────────────────────────┘
                               │
                       [Local Burg Node]
                      - Obsidian Citadel
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
       [Regional Resource]             [Stationed Forces]
          - Elite Shields               - Iron Ore                    


🗺️ STAGE 3: THE AI-DRIVEN MAP SYNTHESIZER
Only when the user is satisfied with the structural knowledge base do they click "Synthesize World Map". The AI then accesses the database, compiles the spatial constraints, and generates the geography, biomes, and overlays to match the written lore.
       [PROSE LORE NOTEBOOK] ───> [SQL RELATIONAL SCHEMAS]
                                           │
                                           ▼
                                 [CONSTRAINT SOLVER]
                                           │
                                           ▼
 ┌───────────────────────────────────────────────────────────────────────────────────┐
 │                             MAP PROCEDURAL SIMULATOR                              │
 ├───────────────────────────────────────────────────────────────────────────────────┤
 │ 1. Voronoi Mesh Generation                                                        │
 │ 2. Heightmap Seeding (Sets Elevation = Mountain over Obsidian Citadel coordinates)│
 │ 3. Climate, Wind & Orographic Precipitation Simulation                            │
 │ 4. Whittaker Biome Generation (Forces Polar Tundra over North Reach)              │
 │ 5. Dijkstra Growth (Seeds Vulfurn Empire capital at the Obsidian Citadel cell)    │
 │ 6. Local Road Pathfinding & Commmodity Distribution                               │
 └───────────────────────────────────────────────────────────────────────────────────┘


How the Simulation Layers are Synthesized from Prose:
Elevation Seeding: The engine reads geographical indicators like "Volcanic Area" and "Chasms" from the database. It maps the Obsidian Citadel to a specific cell index, raising its terrain value () while carving out steep adjacent clefts.
Moisture & Climate Realization: The engine reads "Frozen Wastes" and "Subpolar" indicators. It positions the cell index in the northern polar wind band zone, forcing temperatures below  to generate a tundra biome.
Political Expansion: The Dijkstra expansion loop seeds the Vulfurn Empire's primary capital exactly on the Obsidian Citadel’s cell, letting its territory expand outward, colored in deep crimson (#ef4444).
Religions & Cultures Mapping: The system paints Boreal Elves and the Eternal Dawn across the surrounding cells, following the written constraint: "Boreal Elves who worship the Eternal Dawn surround the citadel".
Economic Distribution: The cell's production good is set to "Iron Ore", and a trade route is drawn connecting the Obsidian Citadel to its closest coastal shipping lanes.
🎨 THE REBUILDING ROADMAP
To implement this workflow, we must refactor our desktop code into clean, modular blocks:
⚙️ Step 1: The Relational DB Core & Setup
We will update our SQL manager to construct the fully interconnected, foreign-key-constrained database, ensuring all tables are initialized instantly on boot.
📁 Step 2: The Ingestion & AI Entity Dissector
We will write the background worker that scans your markdown directory, prompts Ollama with structured JSON schemas, parses out characters, factions, burgs, and climates, and commits them to the database.
🗺️ Step 3: The Constraint-Driven Map Generator
We will build the coordinate solver inside AzgaarEngine. Instead of random simplex noise, the heightmap generator will accept the extracted spatial anchors, generating mountains, rivers, and political spheres precisely where your stories dictate.
🎨 Step 4: Symmetrical PyQt6 Layout Integration
We will configure the dual-bay window. The Left Bay displays the editable spreadsheets for your structured lore; the Center Bay holds the notebook; and the Right Bay contains the visualization map viewer and paintbrushes to fine-tune the synthesized map.
