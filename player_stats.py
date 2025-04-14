from flask import Flask, jsonify, request
from understat import Understat
import asyncio
import aiohttp
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)

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

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    data = loop.run_until_complete(fetch_data(player_id, season))
    return jsonify(data)

@app.route('/search_player')
def search_player():
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

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    players = loop.run_until_complete(fetch_all_players())

    matched_players = [p for p in players if name in p['player_name'].lower()]

    return jsonify(matched_players[:5])

if __name__ == "__main__":
    app.run(debug=True)
