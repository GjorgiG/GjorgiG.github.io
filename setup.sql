CREATE TABLE IF NOT EXISTS player_vectors (
    id INTEGER PRIMARY KEY,
    name TEXT,
    team TEXT,
    vector FLOAT8[]
);

CREATE TABLE IF NOT EXISTS similar_players (
    player_id INTEGER,
    similar_id INTEGER,
    similarity FLOAT8,
    PRIMARY KEY (player_id, similar_id)
);
