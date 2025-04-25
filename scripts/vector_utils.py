import numpy as np

def safe_float(val):
    try:
        return float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return 0.0

def vectorize(seasons):
    total_time = 0
    totals = {
        'goals': 0,
        'xG': 0,
        'shots': 0,
        'assists': 0,
        'xA': 0,
        'key_passes': 0,
        'xGChain': 0,
        'xGBuildup': 0,
    }

    for season in seasons:
        time = safe_float(season.get('time'))
        total_time += time
        for k in totals:
            totals[k] += safe_float(season.get(k))

    if total_time == 0:
        return [0.0] * len(totals)

    return [totals[k] / (total_time / 90) for k in totals]

def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    return float(np.dot(a, b) / (norm_a * norm_b)) if norm_a and norm_b else 0
