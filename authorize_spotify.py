import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json

# Load credentials from config file
with open('config/config.json', 'r') as f:
    config = json.load(f)

CLIENT_ID = config['music']['spotify_client_id']
CLIENT_SECRET = config['music']['spotify_client_secret']
REDIRECT_URI = config['music']['spotify_redirect_uri']

# Select "scopes" (permissions) you need
# Full list: https://developer.spotify.com/documentation/web-api/concepts/scopes
SCOPE = config['music']['spotify_scope']

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
))

# Test: Get your current playing track
try:
    current_track = sp.current_user_playing_track()
    if current_track:
        name = current_track['item']['name']
        artist = current_track['item']['artists'][0]['name']
        print(f"Currently playing: {name} by {artist}")
    else:
        print("Nothing is currently playing.")
except Exception as e:
    print(f"Auth failed: {e}")