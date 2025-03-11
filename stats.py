from flask import Flask, jsonify
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
    async def fetch_data():
        client = UnderstatClient()
        
        team_match_data = client.team(team="Manchester_United").get_match_data(season="2025")
        
        return team_match_data

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    data = loop.run_until_complete(fetch_data())
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
