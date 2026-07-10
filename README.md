# Worldsmith Sandbox

Worldsmith Sandbox is a procedural fantasy map generator and worldbuilding suite powered by a high-performance Python engine, a rich PyQt6 interface, and integrated local LLM capabilities via Ollama. 

It aims to provide a unified environment for generating Voronoi-based terrain, simulating hydrology and biomes, placing settlements, and curating an interconnected lore database.

## Features

- **Procedural Engine**: Generates a customizable Voronoi mesh, simulating tectonic plates, heightmaps, rivers, and biomes.
- **Interactive Map Canvas**: Fully interactable panning and zooming UI for viewing heightmaps, cultures, states, and relief icons.
- **Magic Brushes**: Modify terrain, borders, and state ownership directly on the map.
- **Lore Database**: Interconnected notes system backed by a local SQLite database (`lore_forge_world.db`).
- **AI Integration**: The AI acts purely as an analytical assistant using Ollama. It audits your timeline for continuity, organizes your thoughts, and encourages new lore creation by identifying gaps. All creative writing is done entirely by you.

## Installation

1. Ensure Python 3.9+ is installed.
2. Clone this repository.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. If you want to use the AI features, install and run [Ollama](https://ollama.com/) locally.

## Usage

Start the main application UI:
```bash
python -m python_fmg.main
```

You can also run the automated UI fuzzers and End-to-End simulation tests in the `tests/` directory:
```bash
python -m tests.auto_tester
python -m tests.e2e_tester
```

## Documentation
See the `docs/` folder for comprehensive documentation:
- [Architecture](docs/architecture.md): Overview of the engine, database, and UI.
- [User Guide](docs/user_guide.md): Instructions on map brushes and lore tools.
- [Testing](docs/testing.md): Automated UI fuzzer and E2E simulation details.

## Contributing

We welcome contributions! To ensure stability, please run the automated test suites before submitting a pull request:

```bash
# Run the autonomous UI fuzzer to catch signal errors
python -m tests.auto_tester

# Run the End-to-End simulation to verify map logic and database persistence
python -m tests.e2e_tester
```

Please see our [Architecture](docs/architecture.md) documentation for an overview of the codebase before making structural changes.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
