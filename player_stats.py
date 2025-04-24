from flask import Flask, jsonify, request, make_response
from understat import Understat
import asyncio
import aiohttp
from flask_cors import CORS
import numpy as np
import nest_asyncio

nest_asyncio.apply()

app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

@app.route('/')
def index():
    return app.send_static_file('player-stats.html')

@app.route('/get_shots')
def get_shots():
    player_id = request.args.get('player_id')
    season = request.args.get('season')

    if not player_id or not season:
        return jsonify({'error': 'player_id and season are required'}), 400

    async def fetch_data(pid, season):
        async with aiohttp.ClientSession() as session:
            understat = Understat(session)
            shots = await understat.get_player_shots(player_id=pid, season=season)
            return shots

    loop = asyncio.get_event_loop()
    data = loop.run_until_complete(fetch_data(player_id, season))
    return jsonify(data)

@app.route('/get_radar_stats')
def get_radar_stats():
    player_id = request.args.get('player_id')
    if not player_id:
        return jsonify({'error': 'player_id is required'}), 400

    async def fetch_radar(pid):
        async with aiohttp.ClientSession() as session:
            understat = Understat(session)
            stats = await understat.get_player_stats(player_id=pid)
            return stats[0] if stats else {}

    loop = asyncio.get_event_loop()
    data = loop.run_until_complete(fetch_radar(player_id))
    return jsonify(data)

@app.route('/get_grouped_stats')
def get_grouped_stats():
    player_id = request.args.get('player_id')
    if not player_id:
        return jsonify({'error': 'player_id is required'}), 400

    async def fetch_grouped(pid):
        async with aiohttp.ClientSession() as session:
            understat = Understat(session)
            grouped = await understat.get_player_grouped_stats(player_id=pid)
            return grouped

    loop = asyncio.get_event_loop()
    data = loop.run_until_complete(fetch_grouped(player_id))
    return jsonify(data)

def safe_float(val):
    try:
        if isinstance(val, dict) and 'value' in val:
            return float(val['value'])
        return float(val)
    except:
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

@app.route('/get_similar_players', methods=['OPTIONS', 'GET'])
def get_similar_players():

    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers['Access-Control-Allow-Origin']  = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp
    
    player_id = request.args.get('player_id')
    if not player_id:
        return jsonify({'error': 'player_id is required'}), 400

    async def fetch_similar():
        async with aiohttp.ClientSession() as session:
            understat = Understat(session)
            try:
                target_stats = await understat.get_player_stats(player_id=int(player_id))
                if not target_stats:
                    return []
                target_vector = vectorize(target_stats[0])
            except Exception as e:
                print(f"[ERROR] Target player stats: {e}")
                return []

            season = "2023"
            teams = ['Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford', 'Brighton',
                     'Chelsea', 'Crystal Palace', 'Everton', 'Fulham', 'Ipswich', 'Leicester',
                     'Liverpool', 'Manchester City', 'Manchester United', 'Newcastle United',
                     'Nottingham Forest', 'Southampton', 'Tottenham', 'West Ham', 'Wolverhampton Wanderers']
            players = []
            for team in teams:
                try:
                    team_players = await understat.get_team_players(team_name=team, season=season)
                    for player in team_players:
                        pid = player.get("id")
                        if not pid or str(pid) == request.args.get("player_id"):
                            continue
                        try:
                            stats = await understat.get_player_stats(player_id=pid)
                            if not stats:
                                continue
                            vec = vectorize(stats[0])
                            sim = cosine_similarity(target_vector, vec)
                            players.append({
                                "player_name": player["player_name"],
                                "team": player.get("team", ""),
                                "similarity": round(sim, 3)
                            })
                        except Exception as e:
                            print(f"Skipping {player['player_name']} due to stats error: {e}")
                            continue
                except Exception as e:
                    print(f"Team loop error for {team}: {e}")
                    continue

            return sorted(players, key=lambda x: x["similarity"], reverse=True)[:10]
        
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        similar = loop.run_until_complete(fetch_similar())
        response = jsonify(similar)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        print(f"Main error: {str(e)}")
        response = jsonify([])
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

@app.route('/search_player', methods=['GET', 'OPTIONS'])
def search_player():

    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers['Access-Control-Allow-Origin']  = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp
    
    name = request.args.get('name', '').lower()
    season = request.args.get('season', '2022')

    async def fetch_all_players():
        async with aiohttp.ClientSession() as session:
            understat = Understat(session)
            all_players = []
            teams = ['Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford', 'Brighton',
                     'Chelsea', 'Crystal Palace', 'Everton', 'Fulham', 'Ipswich', 'Leicester',
                     'Liverpool', 'Manchester City', 'Manchester United', 'Newcastle United',
                     'Nottingham Forest', 'Southampton', 'Tottenham', 'West Ham', 'Wolverhampton Wanderers']

            for team in teams:
                try:
                    players = await understat.get_team_players(team_name=team, season=season)
                    for player in players:
                        player['team'] = team
                    all_players.extend(players)
                except:
                    continue
            return all_players

    try:
        loop = asyncio.get_event_loop()
        asyncio.set_event_loop(loop)
        players = loop.run_until_complete(fetch_all_players())

        matched_players = [p for p in players if name in p['player_name'].lower()]

        return jsonify(matched_players[:5])
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    except Exception as e:
        print(f"[ERROR] search_player: {e}")
        return jsonify([]), 500

if __name__ == "__main__":
    app.run(debug=True)
