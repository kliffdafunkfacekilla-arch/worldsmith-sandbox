import sqlite3
import random
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lore_forge_world.db"))

class WorldSimulator:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        self.setup_tables()

    def setup_tables(self):
        """Ensures we have tables to track the daily economy and events."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS faction_economy (
                state_id INTEGER PRIMARY KEY,
                food_stockpile INTEGER DEFAULT 50000,
                wealth_stockpile INTEGER DEFAULT 10000,
                ruling_stability INTEGER DEFAULT 100
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                burg_id INTEGER,
                event_type TEXT,
                severity INTEGER,
                resolved INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def run_daily_tick(self):
        """Advances the world by 24 hours."""
        print("=== Advancing World Time: 1 Day ===")
        
        # 1. Get all active states from the Azgaar map data
        self.cursor.execute("SELECT state_id, lore_name FROM azgaar_states")
        states = self.cursor.fetchall()
        
        for state_id, state_name in states:
            # Ensure the state has an economy tracker
            self.cursor.execute("INSERT OR IGNORE INTO faction_economy (state_id) VALUES (?)", (state_id,))
            
            # 2. Calculate Total Population for this State
            self.cursor.execute("""
                SELECT SUM(population) 
                FROM azgaar_burgs 
                WHERE state_id = (SELECT azgaar_original_name FROM azgaar_states WHERE state_id = ?)
            """, (state_id,))
            total_pop = self.cursor.fetchone()[0] or 0
            
            if total_pop == 0:
                continue

            # 3. The Math: Harvest vs. Consumption
            # Assuming a standard harvest adds a baseline, but populations eat 1 unit of food per 100 people
            daily_harvest = random.randint(100, 500) # In a real build, this scales with farms
            daily_consumption = int(total_pop / 100)
            
            # Update the database stockpile
            self.cursor.execute("""
                UPDATE faction_economy 
                SET food_stockpile = food_stockpile + ? - ?
                WHERE state_id = ?
            """, (daily_harvest, daily_consumption, state_id))
            
            # 4. Check for Starvation (The Tension Generator)
            self.cursor.execute("SELECT food_stockpile FROM faction_economy WHERE state_id = ?", (state_id,))
            current_food = self.cursor.fetchone()[0]
            
            if current_food < 0:
                # Reset to zero and tank stability
                self.cursor.execute("UPDATE faction_economy SET food_stockpile = 0, ruling_stability = ruling_stability - 5 WHERE state_id = ?", (state_id,))
                
                # Spawn a Famine Riot in a random city belonging to this state!
                self.cursor.execute("""
                    SELECT burg_id, lore_name, x_coord, y_coord 
                    FROM azgaar_burgs 
                    WHERE state_id = (SELECT azgaar_original_name FROM azgaar_states WHERE state_id = ?) 
                    ORDER BY RANDOM() LIMIT 1
                """, (state_id,))
                city = self.cursor.fetchone()
                
                if city:
                    burg_id, city_name, x, y = city
                    severity = abs(current_food)
                    print(f"  [!] FAMINE RIOT: {state_name} is starving! Riots break out in {city_name} (X:{x}, Y:{y}).")
                    
                    self.cursor.execute("""
                        INSERT INTO active_events (burg_id, event_type, severity)
                        VALUES (?, 'Famine Riot', ?)
                    """, (burg_id, severity))

        self.conn.commit()
        print("=== Tick Complete. World State Saved. ===\n")

if __name__ == "__main__":
    sim = WorldSimulator()
    # Run a week of simulation
    for day in range(1, 8):
        print(f"--- Day {day} ---")
        sim.run_daily_tick()
