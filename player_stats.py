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

# initialises the flask app
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
    season = request.args.get('season')

    if not player_id or not season:
        return jsonify({'error': 'player_id and season are required'}), 400

    async def fetch_radar(pid, season):
        async with aiohttp.ClientSession() as session:
            understat = Understat(session)
            stats = await understat.get_player_grouped_stats(player_id=pid)

            if not stats or 'season' not in stats:
                return {}
            
            season_stats = next((s for s in stats['season'] if s['season'] == season), None)
            if not season_stats:
                return {}            
            
            minutes = float(season_stats.get('time', 1)) or 1 # stops division by zero

            # returns the p90 stats
            return {
                'G90': float(season_stats.get('goals', 0)) / (minutes / 90),
                'xG90': float(season_stats.get('xG', 0)) / (minutes / 90),
                'Sh90': float(season_stats.get('shots', 0)) / (minutes / 90),
                'A90': float(season_stats.get('assists', 0)) / (minutes / 90),
                'xA90': float(season_stats.get('xA', 0)) / (minutes / 90),
                'KP90': float(season_stats.get('key_passes', 0)) / (minutes / 90),
                'xGChain90': float(season_stats.get('xGChain', 0)) / (minutes / 90),
                'xGBuildup90': float(season_stats.get('xGBuildup', 0)) / (minutes / 90)
            }

    loop = asyncio.get_event_loop()
    data = loop.run_until_complete(fetch_radar(player_id, season))
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

# connects to the postgres database
conn = psycopg2.connect(os.environ['DATABASE_URL'])

# this finds similar players based on their similarity score
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
        with psycopg2.connect(os.environ['DATABASE_URL']) as conn: # this queries the database for similar players
            with conn.cursor() as c:
                c.execute("""
                    SELECT pv.id, pv.name, pv.team, sp.similarity
                    FROM similar_players sp
                    JOIN player_vectors pv ON pv.id = sp.similar_id
                    WHERE sp.player_id = %s
                    ORDER BY sp.similarity DESC
                    LIMIT 10
                """, (player_id,))
                similar = c.fetchall()

        results = [{ # this then formats the results into JSON
            'player_id': row[0],
            'player_name': row[1],
            'team': row[2],
            'similarity': round(row[3], 3)
        } for row in similar]

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
    season = request.args.get('season', '2024')

    # async fetch for every player in the league
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
