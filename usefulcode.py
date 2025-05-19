#example import of spotipy import
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from time import sleep


# Set up Spotify credentials
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="YOUR_APP_CLIENT_ID",
    client_secret="YOUR_APP_CLIENT_SECRET",
    redirect_uri="YOUR_APP_REDIRECT_URI",
    scope="user-top-read,user-library-read,user-read-recently-played"))


# Change volume
sp.volume(100)
sleep(2)
sp.volume(50)
sleep(2)
sp.volume(100)


# Change track
sp.start_playback(uris=['spotify:track:6gdLoMygLsgktydTQ71b15']) #Υποθετω εδω αλλαζει σε καποιο συγκεκριμενο κομματι

# Use the IDs to get some recommendations
# Note: the seed_tracks parameter can accept up to 5 tracks
recommendations = sp.recommendations(
    seed_tracks=seed_track_ids[0:5], limit=10, country='US')

# Display the recommendations
for i, track in enumerate(recommendations['tracks']):
    print(f"{i+1}. {track['name']} by "
          f"{', '.join([artist['name'] for artist in track['artists']])}")
    
#https://github.com/spotipy-dev/spotipy-examples/blob/main/apps/streamlit/app.py
#https://spotipy.readthedocs.io/en/2.25.1/#api-reference