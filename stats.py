from flask import Flask, jsonify
from understatapi import UnderstatClient
import asyncio

app = Flask(__name__)

@app.route('/get_data')
def get_data():
    async def fetch_data():
        client = UnderstatClient()
        # Test to get player stats from Prem 20/21
        players = await client.get_league_players("EPL", 2021)
        return players

    # Run the async function in an event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    data = loop.run_until_complete(fetch_data())
    return jsonify(data)
