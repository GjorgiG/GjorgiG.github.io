import psycopg2
import numpy as np
from vector_utils import cosine_similarity
import os
from dotenv import load_dotenv

load_dotenv()

print("DB URL from env:", os.environ.get('DATABASE_URL'))

conn = psycopg2.connect(os.environ['DATABASE_URL'])
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS similar_players (
        player_id INTEGER,
        similar_id INTEGER,
        similarity DOUBLE PRECISION,
        PRIMARY KEY (player_id, similar_id)
    )
''')

c.execute("SELECT id, vector FROM player_vectors")
players = c.fetchall()

for pid1, vec1_str in players:
    vec1 = np.array(list(map(float, vec1_str.split(','))))
    scores = []

    for pid2, vec2_str in players:
        if pid1 == pid2:
            continue
        vec2 = np.array(list(map(float, vec2_str.split(','))))
        sim = cosine_similarity(vec1, vec2)
        scores.append((pid2, sim))

    top_similar = sorted(scores, key=lambda x: x[1], reverse=True)[:10]
    for sim_pid, sim_score in top_similar:
        c.execute("""
            INSERT INTO similar_players (player_id, similar_id, similarity)
            VALUES (%s, %s, %s)
            ON CONFLICT (player_id, similar_id)
            DO UPDATE SET similarity = EXCLUDED.similarity
        """, (pid1, sim_pid, sim_score))

conn.commit()
conn.close()
