import numpy as np

def safe_float(val):
    try:
        if isinstance(val, dict):
            return float(val.get("value") or 0)
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def vectorize(stats):
    try:
        minutes = max(safe_float(stats.get('time')), 1)
        return [
            safe_float(stats.get('goals')) / minutes,
            safe_float(stats.get('xG')) / minutes,
            safe_float(stats.get('shots')) / minutes,
            safe_float(stats.get('assists')) / minutes,
            safe_float(stats.get('xA')) / minutes,
            safe_float(stats.get('key_passes')) / minutes,
            safe_float(stats.get('xGChain')) / minutes,
            safe_float(stats.get('xGBuildup')) / minutes,
        ]
    except Exception as e:
        print(f"Vectorization error: {e}")
        return [0] * 8

def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    return float(np.dot(a, b) / (norm_a * norm_b)) if norm_a and norm_b else 0
