from flask import Flask, jsonify, request
from understatapi import UnderstatClient
import asyncio
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)

@app.route('/')
def index():

    return app.send_static_file('player-stats.html')

@app.route('/get_data')
def get_data():
    team = request.args.get('team', 'Manchester_United')
    season = request.args.get('season', '2025')

    async def fetch_data(selected_team, selected_season):
        client = UnderstatClient()
        
        return client.team(team=selected_team).get_match_data(season=selected_season)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Call the async function with user-selected team & season
    data = loop.run_until_complete(fetch_data(team, season))
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
