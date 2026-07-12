# Lordsmith Studio

Lordsmith Studio is a procedural fantasy map generator and holistic worldbuilding suite powered by a high-performance Python engine, a rich PyQt6 interface, and integrated local/cloud LLM capabilities. 

It aims to provide a unified environment for generating Voronoi-based terrain, simulating hydrology and biomes, mapping structured societies, and curating an interconnected lore database.

## 🌟 Key Features

### 🗺️ The Map Engine
- **Procedural Voronoi Engine**: Generates a customizable Voronoi mesh, simulating tectonic plates, heightmaps, rivers, and 24 terrestrial/aquatic biomes.
- **Custom Heightmap Uplink**: Upload your own 2D `.png` or `.jpg` grayscale heightmap to instantly shape the world's continents.
- **High-Res Biome Tile Rendering**: Features a 1D Euclidean interactive canvas that renders hand-painted biome sprite sheets seamlessly across the hex grid.
- **Dynamic Layers**: Swap between distinct visual mapping layers instantly (States, Provinces, Biomes, Elevation, Rivers, and Magical Leylines).

### 🏛️ The Database & UI Architecture
- **17 Subsystem Matrices**: Manage every aspect of your world across 17 distinct interactive ledger tabs (Factions, Provinces, Religions, Cultures, Military, Trade, Geography, and Shadow Networks).
- **Temporal Mechanics**: Define planetary moons (affecting tides/magic), calendar season configurations, and historical timelines bound to specific coordinate cells.
- **Inspector Window**: Contextually edits fields and synchronizes instantly across the map.

### ✍️ The Lore Editor
- **Interactive Markdown Notebook**: Write your world's prose inside an interactive editor.
- **Live Syntax Highlighting**: Color-codes and underlines `[[WikiLinks]]` and `(cell_idx: 250)` coordinate tags in real-time.
- **Spatial Click-Binding**: Clicking coordinate nodes within your text will dynamically pan and highlight the map canvas to the exact cell.

### 🧠 The AI Pipeline
- **Lordsmith AI Client**: Employs a 5-stage exponential backoff algorithm that first queries your local **Ollama** endpoint for total privacy, silently failing over to the **Google Gemini API** if offline.
- **Lore Auditor**: Analyzes your prose against the 17 SQL tables to flag ecological, political, or magical contradictions automatically.
- **Bulk Lore Ingestor**: Converts unstructured prose documents into rigidly structured foreign-key JSON nodes.

### 📤 Exporters
- **GeoJSON Framework**: Export your borders, nodes, and cells into standard GIS formats.
- **Static HTML Wiki**: Compiles your entire database of cross-linked notes into a beautiful, static, offline-ready HTML website index.

## Installation

1. Ensure Python 3.9+ is installed.
2. Clone this repository.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. If you want to use the offline AI features, install and run [Ollama](https://ollama.com/) locally.

## Usage

Start the main application UI:
```bash
python python_fmg/main.py
```

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
