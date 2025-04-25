import asyncio
import aiohttp
import psycopg2
import os
from understat import Understat
from vector_utils import vectorize
from dotenv import load_dotenv

load_dotenv()

print("DB URL from env:", os.environ.get('DATABASE_URL'))

teams = ['Arsenal', 'Chelsea', 'Liverpool', 'Manchester City', 'Manchester United', 'Tottenham']
season = "2023"

async def precompute_and_store():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS player_vectors (
            id INTEGER PRIMARY KEY,
            name TEXT,
            team TEXT,
            vector TEXT
        )
    ''')

    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        for team in teams:
            try:
                players = await understat.get_team_players(team_name=team, season=season)
                for player in players:
                    pid = player.get("id")
                    name = player.get("player_name")
                    try:
                        await asyncio.sleep(0.5) 
                        stats = await understat.get_player_grouped_stats(player_id=pid)
                        seasons = stats.get("season")
                        vec = vectorize(seasons)
                        print(f"{name} vector: {vec}")
                        c.execute("""
                            INSERT INTO player_vectors (id, name, team, vector)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE
                            SET name = EXCLUDED.name,
                                team = EXCLUDED.team,
                                vector = EXCLUDED.vector
                        """, (pid, name, team, ','.join(map(str, vec))))
                    except Exception as e:
                        print(f"Vector error for {name}: {e}")
                        continue
            except Exception as e:
                print(f"Team fetch failed: {e}")
                continue

    conn.commit()
    conn.close()

asyncio.run(precompute_and_store())
