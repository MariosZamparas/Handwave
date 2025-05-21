# spotify_gui_pyside.py
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget,
    QHBoxLayout, QSlider, QMessageBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QThread, Signal

import requests
import io
import sys
import os
import time
import cv2
import mediapipe as mp
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Load environment variables and check for required Spotify credentials
def get_spotify_credentials():
    load_dotenv()

    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")

    # Check if keys are valid
    if not all([client_id, client_secret, redirect_uri]):
        show_error(
            "Your .env file is incomplete.\nPlease include SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, and SPOTIPY_REDIRECT_URI."
        )
        sys.exit(1)

    return client_id, client_secret, redirect_uri

def show_error(message, parent=None):
    QMessageBox.critical(parent, "Configuration Error", message)

# === GESTURE THREAD ===
class GestureControlThread(QThread):
    gesture_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.last_gesture = None
        self.last_gesture_time = 0
        self.cooldown = 1.5  # seconds

        self.prev_hand_x = None
        self.prev_hand_y = None  # <-- για vertical gesture

        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(static_image_mode=False,
                                         max_num_hands=1,
                                         min_detection_confidence=0.7,
                                         min_tracking_confidence=0.7)

    def run(self):
        cap = cv2.VideoCapture(0)

        while self.running:
            success, image = cap.read()
            if not success:
                continue

            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = self.hands.process(image_rgb)

            gesture = None
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    landmarks = hand_landmarks.landmark
                    gesture = self.detect_gesture(landmarks)
                    if gesture:
                        break

            current_time = time.time()
            if gesture and (gesture != self.last_gesture or (current_time - self.last_gesture_time > self.cooldown)):
                self.last_gesture = gesture
                self.last_gesture_time = current_time
                self.gesture_signal.emit(gesture)

            cv2.putText(image, f"Gesture: {gesture or 'None'}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Gesture Control", image)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

    def detect_gesture(self, landmarks):
        def is_open_palm(landmarks):
            tips = [8, 12, 16, 20]
            pips = [6, 10, 14, 18]
            return all(landmarks[tip].y < landmarks[pip].y for tip, pip in zip(tips, pips))

        wrist_x = landmarks[0].x
        wrist_y = landmarks[0].y

        direction = None
        v_direction = None

        # Οριζόντια κίνηση
        if self.prev_hand_x is not None:
            dx = wrist_x - self.prev_hand_x
            if dx > 0.05:
                direction = "right"
            elif dx < -0.05:
                direction = "left"
        self.prev_hand_x = wrist_x

        # Κάθετη κίνηση
        if self.prev_hand_y is not None:
            dy = wrist_y - self.prev_hand_y
            if dy < -0.05:
                v_direction = "up"
            elif dy > 0.05:
                v_direction = "down"
        self.prev_hand_y = wrist_y

        if is_open_palm(landmarks):
            return "play_pause"
        elif direction == "right":
            return "next"
        elif direction == "left":
            return "prev"
        elif v_direction == "up":
            return "volume_up"
        elif v_direction == "down":
            return "volume_down"

        return None

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


# === SPOTIFY APP GUI ===
class SpotifyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spotify Media Player")
        self.setGeometry(100, 100, 600, 600)

        self.sp = None
        self.tracks = []
        self.track_index = 0
        self.is_paused = False

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout()

        self.status_label = QLabel("Not logged in")
        self.layout.addWidget(self.status_label)

        self.login_btn = QPushButton("Log In with Spotify")
        self.login_btn.clicked.connect(self.login)
        self.layout.addWidget(self.login_btn)

        self.logout_btn = QPushButton("Log Out")
        self.logout_btn.clicked.connect(self.logout)
        self.logout_btn.setDisabled(True)
        self.layout.addWidget(self.logout_btn)

        self.playlist_list = QListWidget()
        self.playlist_list.itemClicked.connect(self.load_tracks)
        self.layout.addWidget(self.playlist_list)

        self.track_list = QListWidget()
        self.track_list.itemClicked.connect(self.select_track)
        self.layout.addWidget(self.track_list)

        self.track_label = QLabel("No track loaded")
        self.track_label.setWordWrap(True)
        self.layout.addWidget(self.track_label)

        self.album_art = QLabel()
        self.layout.addWidget(self.album_art)

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

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(75)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.layout.addWidget(QLabel("Volume"))
        self.layout.addWidget(self.volume_slider)

        self.main_widget.setLayout(self.layout)

        self.gesture_thread = GestureControlThread()
        self.gesture_thread.gesture_signal.connect(self.handle_gesture)
        self.gesture_thread.start()

    def closeEvent(self, event):
        self.gesture_thread.stop()
        event.accept()

    def handle_gesture(self, gesture):
        print(f"Gesture detected: {gesture}")
        if gesture == "play_pause":
            self.toggle_pause()
        elif gesture == "next":
            self.next_track()
        elif gesture == "prev":
            self.prev_track()
        elif gesture == "volume_up":
            val = min(self.volume_slider.value() + 10, 100)
            self.volume_slider.setValue(val)
        elif gesture == "volume_down":
            val = max(self.volume_slider.value() - 10, 0)
            self.volume_slider.setValue(val)

    def login(self):
        try:
            client_id, client_secret, redirect_uri = get_spotify_credentials()

            scope = (
                "user-read-playback-state user-modify-playback-state "
                "playlist-read-private playlist-read-collaborative"
            )
            auth_manager = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=scope,
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
            show_error(f"Login Failed:\n{str(e)}", parent=self)


    def logout(self):
        for f in os.listdir(os.path.dirname(os.path.abspath(__file__))):
            if f.startswith(".cache"):
                try:
                    os.remove(f)
                except:
                    pass
        self.sp = None
        self.tracks = []
        self.track_index = 0
        self.is_paused = False
        self.status_label.setText("Not logged in")
        self.login_btn.setDisabled(False)
        self.logout_btn.setDisabled(True)
        self.playlist_list.clear()
        self.track_list.clear()

    def load_playlists(self):
        try:
            self.playlist_list.clear()
            playlists = self.sp.current_user_playlists()
            self.playlist_data = playlists['items']
            for p in self.playlist_data:
                self.playlist_list.addItem(p['name'])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load playlists:\n{e}")

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

    def select_track(self, item):
        self.track_index = self.track_list.row(item)
        self.update_track_display()

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

    def play_track(self):
        try:
            track = self.tracks[self.track_index]
            uri = track['uri']
            devices = self.sp.devices()
            active_device = next((d for d in devices['devices'] if d['is_active']), None)
            if not active_device:
                QMessageBox.warning(self, "No Device", "Open Spotify on a device.")
                return
            self.sp.start_playback(device_id=active_device['id'], uris=[uri])
            self.is_paused = False
            self.update_track_display()
        except Exception as e:
            QMessageBox.critical(self, "Playback Error", str(e))

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

    def set_volume(self, val):
        try:
            self.sp.volume(val)
        except Exception as e:
            QMessageBox.critical(self, "Volume Error", str(e))

    def next_track(self):
        try:
            self.sp.next_track()
            if self.track_index < len(self.tracks) - 1:
             self.track_index += 1
             self.update_track_display()
        except Exception as e:
         QMessageBox.critical(self, "Next Track Error", str(e))

    def prev_track(self):
        try:
            self.sp.previous_track()
            if self.track_index > 0:
             self.track_index -= 1
            self.update_track_display()
        except Exception as e:
         QMessageBox.critical(self, "Previous Track Error", str(e))



# === ENTRY POINT ===
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SpotifyApp()
script_dir = os.path.dirname(os.path.abspath(__file__))
style_path = os.path.join(script_dir, "style.qss")
with open(style_path, "r") as f:
      app.setStyleSheet(f.read())
      window.show()
      sys.exit(app.exec())
