import sqlite3
import requests
import json
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lore_forge_world.db"))
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:latest" # Ensure this matches your local model

def init_story_table():
    """Creates a table to store the generated narrative lore."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generated_lore (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            location TEXT,
            narrative_text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def fetch_unresolved_events():
    """Grabs raw events and joins them with physical map data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Join the event with the specific City and State it happened in
    # Note: azgaar_burgs.state_id actually contains the string name, so we join on azgaar_original_name
    cursor.execute("""
        SELECT e.event_id, e.event_type, e.severity, b.lore_name, s.lore_name 
        FROM active_events e
        JOIN azgaar_burgs b ON e.burg_id = b.burg_id
        JOIN azgaar_states s ON b.state_id = s.azgaar_original_name
        WHERE e.resolved = 0
    """)
    events = cursor.fetchall()
    conn.close()
    return events

def generate_narrative(event_data):
    """Sends the strict context package to the local LLM."""
    event_id, event_type, severity, city_name, faction_name = event_data
    
    print(f"-> Weaving story for {event_type} in {city_name} ({faction_name})...")
    
    # The Contextual Prompt
    prompt = f"""
    You are the canonical Game Master and lore archivist for a dark fantasy world. 
    Translate the following simulation data into a 3-sentence immersive rumor that players might hear in a tavern.
    
    SIMULATION DATA:
    - Location: {city_name}
    - Faction in Control: {faction_name}
    - Event: {event_type}
    - Severity Level: {severity} (Scale of 1 to 100)
    
    RULES:
    - Do not invent new factions or cities.
    - Focus heavily on the gritty, physical reality of the event.
    - Output ONLY the 3-sentence rumor text. No greetings, no markdown.
    """
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "1h"
    }
    
    try:
        # Standard API call to local Ollama instance
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"  [!] LLM Generation Error: {e}")
        return None

def mark_event_resolved(event_id, narrative, city_name):
    """Saves the story to the database and closes the event."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Save the generated text
    cursor.execute("""
        INSERT INTO generated_lore (event_id, location, narrative_text)
        VALUES (?, ?, ?)
    """, (event_id, city_name, narrative))
    
    # Mark the raw simulation event as resolved so we don't process it again
    cursor.execute("UPDATE active_events SET resolved = 1 WHERE event_id = ?", (event_id,))
    
    conn.commit()
    conn.close()

def main():
    init_story_table()
    events = fetch_unresolved_events()
    
    if not events:
        print("No new events to process.")
        return
        
    print(f"Found {len(events)} unresolved events. Waking up LLM...")
    
    # Just do a small batch of 5 to show it works, since LLM takes time
    for event in events[:5]:
        narrative = generate_narrative(event)
        if narrative:
            print(f"\n[Generated Rumor for {event[3]}]:\n{narrative}\n")
            mark_event_resolved(event[0], narrative, event[3])
            
    if len(events) > 5:
        print(f"\nProcessed 5 events to demonstrate. ({len(events)-5} remain unresolved in database)")
    print("Story weaving complete.")

if __name__ == "__main__":
    main()
