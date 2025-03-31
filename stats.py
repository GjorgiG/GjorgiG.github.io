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

@app.route('/get_data')
def get_data():
    team = request.args.get('team', 'Manchester United')
    season = request.args.get('season', '2022')

    async def fetch_data(selected_team, selected_season):
        async with aiohttp.ClientSession() as session:
            understat = Understat(session)
            data = await understat.get_team_games_data(team_name=selected_team, season=selected_season)
            return data

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    data = loop.run_until_complete(fetch_data(team, season))
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
