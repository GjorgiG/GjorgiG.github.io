from flask import Flask, jsonify, request, make_response
from understat import Understat
import asyncio
import aiohttp
from flask_cors import CORS
import numpy as np
import nest_asyncio
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
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

def safe_float(v: object) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v or 0)
        except ValueError:
            return 0.0
    if isinstance(v, dict):
        for key in ('90s', 'n', 'value', 'total', 'sum'):
            if key in v:
                return safe_float(v[key])
        return 0.0
    return 0.0

@app.route('/get_radar_stats')
def get_radar_stats():
    player_id = request.args.get('player_id')
    if not player_id:
        return jsonify({'error': 'player_id is required'}), 400

    async def fetch_radar(pid):
        async with aiohttp.ClientSession() as session:
            understat = Understat(session)
            stats = await understat.get_player_stats(player_id=pid)
            if not stats:
                return {}

            totals = {
                "goals": 0.0, "xG": 0.0, "shots": 0.0,
                "assists": 0.0, "xA": 0.0, "key_passes": 0.0,
                "xGChain": 0.0, "xGBuildup": 0.0, "minutes": 0.0
            }

            for s in stats:
                totals["minutes"] += safe_float(s.get("time"))         
                totals["goals"] += safe_float(s.get("goals"))
                totals["xG"] += safe_float(s.get("xG"))
                totals["shots"] += safe_float(s.get("shots"))
                totals["assists"] += safe_float(s.get("assists"))
                totals["xA"] += safe_float(s.get("xA"))
                totals["key_passes"] += safe_float(s.get("key_passes"))
                totals["xGChain"] += safe_float(s.get("xGChain"))
                totals["xGBuildup"] += safe_float(s.get("xGBuildup"))

            mins = totals["minutes"]
            if mins == 0:
                return {}

            per90 = lambda v: v * 90 / mins

            return {
                "G90": per90(totals["goals"]),
                "xG90": per90(totals["xG"]),
                "Sh90": per90(totals["shots"]),
                "A90": per90(totals["assists"]),
                "xA90": per90(totals["xA"]),
                "KP90": per90(totals["key_passes"]),
                "xGChain90": per90(totals["xGChain"]),
                "xGBuildup90": per90(totals["xGBuildup"]),
            }

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

conn = psycopg2.connect(os.environ['DATABASE_URL'])

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

    try:
        c = conn.cursor()
        c.execute("""
            SELECT pv.id, pv.name, pv.team, sp.similarity
            FROM similar_players sp
            JOIN player_vectors pv ON pv.id = sp.similar_id
            WHERE sp.player_id = %s
            ORDER BY sp.similarity DESC
            LIMIT 10
        """, (player_id,))
        similar = c.fetchall()

        results = []
        for sim in similar:
            results.append({
                'player_id': sim[0],
                'player_name': sim[1],
                'team': sim[2],
                'similarity': round(sim[3], 3)
            })
        
        resp = jsonify(results)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    except Exception as e:
        print(f"[ERROR] fetching similar players: {e}")
        resp = jsonify([])
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp

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
