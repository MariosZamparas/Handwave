# spotify_gui_pyside.py

# GUI framework
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget,
    QHBoxLayout, QSlider, QMessageBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

# External libraries
import requests
import io
import sys
import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Load .env environment variables
load_dotenv()

# Spotify API credentials
CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')
SCOPE = 'user-read-private user-read-email playlist-read-private user-modify-playback-state user-read-playback-state'

# Main application class
class SpotifyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spotify Media Player")
        self.setGeometry(100, 100, 600, 600)

        # Playback and state variables
        self.sp = None
        self.tracks = []
        self.track_index = 0
        self.is_paused = False

        # Main layout container
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout()

        # Login status label
        self.status_label = QLabel("Not logged in")
        self.layout.addWidget(self.status_label)

        # Auth buttons
        self.login_btn = QPushButton("Log In with Spotify")
        self.login_btn.clicked.connect(self.login)
        self.layout.addWidget(self.login_btn)

        self.logout_btn = QPushButton("Log Out")
        self.logout_btn.clicked.connect(self.logout)
        self.logout_btn.setDisabled(True)
        self.layout.addWidget(self.logout_btn)

        # Playlist and track list
        self.playlist_list = QListWidget()
        self.playlist_list.itemClicked.connect(self.load_tracks)
        self.layout.addWidget(self.playlist_list)

        self.track_list = QListWidget()
        self.track_list.itemClicked.connect(self.select_track)
        self.layout.addWidget(self.track_list)

        # Selected track display
        self.track_label = QLabel("No track loaded")
        self.track_label.setWordWrap(True)
        self.layout.addWidget(self.track_label)

        # Album art display
        self.album_art = QLabel()
        self.layout.addWidget(self.album_art)

        # Playback control buttons
        control_layout = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.play_track)
        control_layout.addWidget(self.play_btn)

        self.pause_btn = QPushButton("Pause/Resume")
        self.pause_btn.clicked.connect(self.toggle_pause)
        control_layout.addWidget(self.pause_btn)

        self.prev_btn = QPushButton("Prev")
        self.prev_btn.clicked.connect(self.prev_track)
        control_layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self.next_track)
        control_layout.addWidget(self.next_btn)

        self.layout.addLayout(control_layout)

        # Volume control
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(75)  # Default volume
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.layout.addWidget(QLabel("Volume"))
        self.layout.addWidget(self.volume_slider)

        # Apply layout to central widget
        self.main_widget.setLayout(self.layout)

    # Spotify login logic
    def login(self):
        try:
            auth_manager = SpotifyOAuth(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri=REDIRECT_URI,
                scope=SCOPE,
                cache_path=".cache",
                open_browser=True
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            user = self.sp.current_user()
            name = user.get('display_name', 'Unknown')
            self.status_label.setText(f"Logged in as {name}")
            self.logout_btn.setDisabled(False)
            self.login_btn.setDisabled(True)
            self.load_playlists()
        except Exception as e:
            QMessageBox.critical(self, "Login Failed", str(e))

    # Logout and reset UI
    def logout(self):
        for f in os.listdir(os.path.dirname(os.path.abspath(__file__))):
            if f.startswith(".cache"):
                try: os.remove(f)
                except: pass
        self.sp = None
        self.tracks = []
        self.track_index = 0
        self.is_paused = False
        self.status_label.setText("Not logged in")
        self.login_btn.setDisabled(False)
        self.logout_btn.setDisabled(True)
        self.playlist_list.clear()
        self.track_list.clear()

    # Fetch and display playlists
    def load_playlists(self):
        try:
            self.playlist_list.clear()
            playlists = self.sp.current_user_playlists()
            self.playlist_data = playlists['items']
            for p in self.playlist_data:
                self.playlist_list.addItem(p['name'])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load playlists:\n{e}")

    # Fetch tracks for selected playlist
    def load_tracks(self, item):
        index = self.playlist_list.row(item)
        playlist_id = self.playlist_data[index]['id']
        try:
            results = self.sp.playlist_items(playlist_id)
            self.tracks = [i['track'] for i in results['items'] if i.get('track')]
            self.track_list.clear()
            for t in self.tracks:
                self.track_list.addItem(f"{t['name']} - {t['artists'][0]['name']}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load tracks:\n{e}")

    # On track selection
    def select_track(self, item):
        self.track_index = self.track_list.row(item)
        self.update_track_display()

    # Show track info and album art
    def update_track_display(self):
        if not self.tracks:
            return
        track = self.tracks[self.track_index]
        self.track_label.setText(f"{track['name']} by {track['artists'][0]['name']}")
        try:
            if track['album']['images']:
                url = track['album']['images'][0]['url']
                img_data = requests.get(url).content
                pixmap = QPixmap()
                pixmap.loadFromData(img_data)
                pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio)
                self.album_art.setPixmap(pixmap)
        except:
            self.album_art.clear()

    # Start playback
    def play_track(self):
        try:
            track = self.tracks[self.track_index]
            uri = track['uri']
            devices = self.sp.devices()
            active_device = next((d for d in devices['devices'] if d['is_active']), None)
            if not active_device:
                QMessageBox.warning(self, "No Device", "Open Spotify on a device.")
                return
            if self.is_paused:
                self.sp.start_playback()
            else:
                self.sp.start_playback(device_id=active_device['id'], uris=[uri])
            self.is_paused = False
        except Exception as e:
            QMessageBox.critical(self, "Playback Error", str(e))

    # Toggle pause/resume
    def toggle_pause(self):
        try:
            if self.is_paused:
                self.sp.start_playback()
                self.is_paused = False
            else:
                self.sp.pause_playback()
                self.is_paused = True
        except Exception as e:
            QMessageBox.critical(self, "Pause/Resume Error", str(e))

    # Adjust volume
    def set_volume(self, val):
        try:
            self.sp.volume(val)
        except Exception as e:
            QMessageBox.critical(self, "Volume Error", str(e))

    # Move to next track
    def next_track(self):
        if self.track_index < len(self.tracks) - 1:
            self.track_index += 1
            self.update_track_display()

    # Move to previous track
    def prev_track(self):
        if self.track_index > 0:
            self.track_index -= 1
            self.update_track_display()

# Application entry point
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SpotifyApp()
    window.show()
    sys.exit(app.exec())
