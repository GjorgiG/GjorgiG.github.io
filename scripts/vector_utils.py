import numpy as np

def safe_avg(val):
    try:
        if isinstance(val, dict):
            return float(val.get("avg") or 0)
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def vectorize(stats):
    try:
        return [
            safe_avg(stats.get('goals')),
            safe_avg(stats.get('xG')),
            safe_avg(stats.get('shots')),
            safe_avg(stats.get('assists')),
            safe_avg(stats.get('xA')),
            safe_avg(stats.get('key_passes')),
            safe_avg(stats.get('xGChain')),
            safe_avg(stats.get('xGBuildup')),
        ]
    except Exception as e:
        print(f"Vectorization error: {e}")
        return [0] * 8

def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    return float(np.dot(a, b) / (norm_a * norm_b)) if norm_a and norm_b else 0
