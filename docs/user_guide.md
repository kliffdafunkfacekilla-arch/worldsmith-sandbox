# Worldsmith User Guide

Welcome to the Worldsmith Sandbox. This guide details how to interact with the UI.

## Navigating the Map
The right-hand side of the application is a fully interactive canvas.
- **Pan**: Click and drag using the **Right Mouse Button** or **Middle Mouse Button** to move around the map.
- **Zoom**: Use the mouse scroll wheel to zoom in and out.
- **Layers**: The toolbar directly above the map allows you to toggle different overlay layers, such as States, Biomes, Religions, and Heightmaps.

## The Magic Brushes
Above the map, you can select different "Paint" modes (such as Height Paint, Burg Paint, State Paint, and River Paint).
1. Select a Brush tool from the combobox.
2. Left-click anywhere on the map canvas to apply the brush. 
3. *Note: You may be prompted to enter a size or intensity value depending on the active brush.*

## Lore & Notebook
The left panel contains your Lore Forge. You can create interconnected Markdown notes representing characters, factions, and cities.
- **New Note**: Select "New Note..." from the dropdown to start writing.
- **Save Note**: Click the "Save" icon to persist your draft into the local SQLite database.
- **Audit Timeline**: The AI will read your currently open note against the rest of the database and alert you to any logical continuity errors or timeline paradoxes.

## Interacting with the AI
At the bottom of the left panel, you'll find an AI chat terminal. Simply type a question or prompt and press Enter. The Worldsmith Assistant will stream a response utilizing your local Ollama installation, grounding its answers in your world's lore.
