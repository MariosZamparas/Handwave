# spotify_gui_pyside.py

import os
import sys
import time
import cv2
import requests
import mediapipe as mp
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QHBoxLayout, QSlider, QTextEdit
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QThread, Signal

# === Constants ===
SCOPE = (
    'user-read-private user-read-email playlist-read-private '
    'user-modify-playback-state user-read-playback-state'
)

# === Utility Functions ===
def show_error(message, console=None):
    if console:
        console.append(f"[ERROR] {message}")
        console.ensureCursorVisible()
    else:
        print(f"[ERROR] {message}")

def check_env():
    if not os.path.isfile('.env'):
        raise FileNotFoundError("Missing .env file. Please place a valid .env in the app folder.")

    load_dotenv()
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")

    if not all([client_id, client_secret, redirect_uri]):
        raise ValueError("Your .env file is incomplete. Please include SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, and SPOTIPY_REDIRECT_URI.")

    return client_id, client_secret, redirect_uri

# === Gesture Recognition Thread ===
class GestureControlThread(QThread):
    gesture_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.last_gesture = None
        self.last_gesture_time = 0
        self.cooldown = 3
        self.prev_hand_x = None
        self.prev_hand_y = None 

        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )

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
                    gesture = self.detect_gesture(hand_landmarks.landmark)
                    if gesture:
                        break

            current_time = time.time()
            if gesture and (
                gesture != self.last_gesture or
                (current_time - self.last_gesture_time > self.cooldown)
            ):
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

        direction, v_direction = None, None

        if self.prev_hand_x is not None:
            dx = wrist_x - self.prev_hand_x
            if dx > 0.05:
                direction = "right"
            elif dx < -0.05:
                direction = "left"
        self.prev_hand_x = wrist_x

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

# === Main Spotify GUI ===
class SpotifyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spotify Media Player")
        self.setGeometry(100, 100, 600, 700)

        self.sp = None
        self.tracks = []
        self.track_index = 0
        self.is_paused = False

        self.init_ui()

        self.gesture_thread = GestureControlThread()
        self.gesture_thread.gesture_signal.connect(self.handle_gesture)
        self.gesture_thread.start()

    def init_ui(self):
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout()

        self.status_label = QLabel("Not logged in")
        self.layout.addWidget(self.status_label)

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet("""
            background-color: #111;
            color: red;
            font-family: Consolas, monospace;
            font-size: 12px;
        """)
        self.console_output.setPlaceholderText("Status / error messages will appear here...")
        self.layout.addWidget(self.console_output)

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
        for text, slot in [
            ("Play", self.play_track),
            ("Pause/Resume", self.toggle_pause),
            ("Prev", self.prev_track),
            ("Next", self.next_track)
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            control_layout.addWidget(btn)

        self.layout.addLayout(control_layout)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(75)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.layout.addWidget(QLabel("Volume"))
        self.layout.addWidget(self.volume_slider)

        self.main_widget.setLayout(self.layout)

    def closeEvent(self, event):
        self.gesture_thread.stop()
        event.accept()

    def handle_gesture(self, gesture):
        if gesture == "play_pause":
            self.toggle_pause()
        elif gesture == "next":
            self.next_track()
        elif gesture == "prev":
            self.prev_track()
        elif gesture == "volume_up":
            self.volume_slider.setValue(min(self.volume_slider.value() + 10, 100))
        elif gesture == "volume_down":
            self.volume_slider.setValue(max(self.volume_slider.value() - 10, 0))

    def login(self):
        try:
            client_id, client_secret, redirect_uri = check_env()
            auth_manager = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=SCOPE,
                cache_path=".cache",
                open_browser=True
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            user = self.sp.current_user()
            name = user.get('display_name', 'Unknown')
            self.status_label.setText(f"Logged in as {name}")
            self.login_btn.setDisabled(True)
            self.logout_btn.setDisabled(False)
            self.console_output.append("[INFO] Login successful.")
            self.load_playlists()
        except Exception as e:
            show_error(f"Login Failed:\n{e}", console=self.console_output)

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
        self.console_output.append("[INFO] Logged out.")

    def load_playlists(self):
        try:
            self.playlist_list.clear()
            playlists = self.sp.current_user_playlists()
            self.playlist_data = playlists['items']
            for p in self.playlist_data:
                self.playlist_list.addItem(p['name'])
        except Exception as e:
            show_error(f"Could not load playlists:\n{e}", console=self.console_output)

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
            show_error(f"Failed to load tracks:\n{e}", console=self.console_output)

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
                show_error("No active device found. Open Spotify on a device.", console=self.console_output)
                return
            self.sp.start_playback(device_id=active_device['id'], uris=[uri])
            self.is_paused = False
            self.update_track_display()
        except Exception as e:
            show_error(f"Playback Error:\n{e}", console=self.console_output)

    def toggle_pause(self):
        try:
            playback = self.sp.current_playback()
            if not playback or not playback.get("device"):
                show_error("No active device found. Start playback on a Spotify app.", console=self.console_output)
                return
            if playback.get("is_playing"):
                self.sp.pause_playback()
                self.is_paused = True
            else:
                self.sp.start_playback()
                self.is_paused = False
        except Exception as e:
            show_error(f"Pause/Resume Error:\n{e}", console=self.console_output)

    def set_volume(self, val):
        try:
            self.sp.volume(val)
        except Exception as e:
            show_error(f"Volume Error:\n{e}", console=self.console_output)

    def next_track(self):
        try:
            if self.track_index < len(self.tracks) - 1:
                self.track_index += 1
            self.play_track()
        except Exception as e:
            show_error(f"Next Track Error:\n{e}", console=self.console_output)

    def prev_track(self):
        if self.track_index == 0:
            return
        try:
            self.track_index -= 1
            self.play_track()
        except Exception as e:
            show_error(f"Previous Track Error:\n{e}", console=self.console_output)

# === Entry Point ===
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SpotifyApp()

    try:
        with open("style.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass

    window.show()
    sys.exit(app.exec())