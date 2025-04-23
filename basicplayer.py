# spotify_gui_refactor.py

# GUI and media/image handling libraries
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import requests
import io
import os

# Spotify API and environment handling
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Load environment variables from .env file
load_dotenv()

# Spotify API credentials
CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')
SCOPE = 'user-read-private user-read-email playlist-read-private user-modify-playback-state user-read-playback-state'

# Main Tkinter app class
class SpotifyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Spotify Media Player")
        self.geometry("500x600")

        # Initialize Spotify and playback state
        self.sp = None
        self.tracks = []
        self.track_index = 0
        self.is_paused = False

        # Main container frame for page switching
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        # Create and store all pages
        self.frames = {}
        for F in (LandingPage, PlaylistPage, PlayerPage):
            frame = F(self.container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(LandingPage)

    def show_frame(self, page):
        frame = self.frames[page]
        frame.tkraise()

    # Handle Spotify OAuth login
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
            self.frames[LandingPage].update_user_info(user)
            self.frames[PlaylistPage].load_playlists()
        except Exception as e:
            messagebox.showerror("Login Failed", str(e))

    # Logout and reset app state
    def logout(self):
        for f in os.listdir(os.path.dirname(os.path.abspath(__file__))):
            if f.startswith(".cache"):
                try: os.remove(f)
                except: pass

        self.sp = None
        self.tracks = []
        self.track_index = 0
        self.is_paused = False
        self.frames[LandingPage].reset()
        self.frames[PlaylistPage].reset()
        self.frames[PlayerPage].reset()
        self.show_frame(LandingPage)

# Navigation bar shared by all pages
class NavigationBar(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        nav = tk.Frame(self)
        nav.pack(pady=5)
        # Center navigation bar buttons using expand and fill
        nav.pack_propagate(False)
        nav.grid_columnconfigure(0, weight=1)
        nav.grid_columnconfigure(1, weight=1)
        nav.grid_columnconfigure(2, weight=1)
        tk.Button(nav, text="Home", width=10, command=lambda: controller.show_frame(LandingPage)).grid(row=0, column=0, padx=10)
        tk.Button(nav, text="Playlists", width=10, command=lambda: controller.show_frame(PlaylistPage)).grid(row=0, column=1, padx=10)
        tk.Button(nav, text="Player", width=10, command=lambda: controller.show_frame(PlayerPage)).grid(row=0, column=2, padx=10)
        nav.pack(fill="x")


# Landing page with login and user info
class LandingPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.label = tk.Label(self, text="Not logged in", font=("Arial", 14))
        self.label.pack(pady=20)
        tk.Button(self, text="Log In with Spotify", command=controller.login).pack(pady=5)
        tk.Button(self, text="Log Out", command=controller.logout).pack(pady=5)
        NavigationBar(self, controller).pack(side="bottom", fill="x")

    def update_user_info(self, user):
        name = user.get('display_name', 'Unknown')
        email = user.get('email', 'N/A')
        self.label.config(text=f"Welcome {name}\nEmail: {email}")

    def reset(self):
        self.label.config(text="Not logged in")

# Playlist selection page
class PlaylistPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.playlist_box = tk.Listbox(self, width=50)
        self.playlist_box.pack(pady=10)
        self.playlist_box.bind("<<ListboxSelect>>", self.load_tracks)

        self.track_box = tk.Listbox(self, width=50)
        self.track_box.pack(pady=10)
        self.track_box.bind("<<ListboxSelect>>", self.select_track)

        NavigationBar(self, controller).pack(side="bottom", fill="x")

    def reset(self):
        self.playlist_box.delete(0, tk.END)
        self.track_box.delete(0, tk.END)

    def load_playlists(self):
        if not self.controller.sp:
            return
        try:
            self.playlist_box.delete(0, tk.END)
            playlists = self.controller.sp.current_user_playlists()
            self.playlist_data = playlists['items']
            for p in self.playlist_data:
                self.playlist_box.insert(tk.END, p['name'])
        except Exception as e:
            messagebox.showerror("Error", f"Could not load playlists:\n{e}")

    def load_tracks(self, event):
        try:
            selection = self.playlist_box.curselection()
            if not selection:
                return
            index = selection[0]
            playlist_id = self.playlist_data[index]['id']
            results = self.controller.sp.playlist_items(playlist_id)
            self.controller.tracks = [item['track'] for item in results['items'] if item.get('track')]
            self.controller.track_index = 0
            self.track_box.delete(0, tk.END)
            for t in self.controller.tracks:
                self.track_box.insert(tk.END, f"{t['name']} - {t['artists'][0]['name']}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load tracks:\n{e}")

    def select_track(self, event):
        selection = self.track_box.curselection()
        if selection:
            self.controller.track_index = selection[0]
            self.controller.frames[PlayerPage].update_track_display()
            self.controller.show_frame(PlayerPage)

# Player page with playback controls
class PlayerPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.track_label = tk.Label(self, text="No track loaded", wraplength=480)
        self.track_label.pack(pady=5)

        self.cover_canvas = tk.Label(self)
        self.cover_canvas.pack(pady=10)

        # Playback control buttons
        controls = tk.Frame(self)
        controls.pack(pady=10)
        tk.Button(controls, text="Play", command=self.play_track).grid(row=0, column=0, padx=5)
        tk.Button(controls, text="Pause/Resume", command=self.toggle_pause).grid(row=0, column=1, padx=5)
        tk.Button(controls, text="Back", command=self.prev_track).grid(row=0, column=2, padx=5)
        tk.Button(controls, text="Next", command=self.next_track).grid(row=0, column=3, padx=5)

        # Volume control
        volume_frame = tk.Frame(self)
        volume_frame.pack(pady=10)
        tk.Label(volume_frame, text="Volume").pack()
        self.volume_slider = tk.Scale(volume_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.set_volume)
        self.volume_slider.set(50)
        self.volume_slider.pack()

        NavigationBar(self, controller).pack(side="bottom", fill="x")

    def reset(self):
        self.track_label.config(text="No track loaded")
        self.cover_canvas.config(image='')

    def update_track_display(self):
        if not self.controller.tracks:
            return
        track = self.controller.tracks[self.controller.track_index]
        self.track_label.config(text=f"{track['name']} by {track['artists'][0]['name']}")
        try:
            if track['album']['images']:
                url = track['album']['images'][0]['url']
                img_data = requests.get(url).content
                img = Image.open(io.BytesIO(img_data)).resize((200, 200))
                self.tk_img = ImageTk.PhotoImage(img)
                self.cover_canvas.config(image=self.tk_img)
        except:
            self.cover_canvas.config(image='')

    def play_track(self):
        try:
            track = self.controller.tracks[self.controller.track_index]
            uri = track['uri']
            devices = self.controller.sp.devices()
            active_device = next((d for d in devices['devices'] if d['is_active']), None)
            if not active_device:
                messagebox.showerror("No Active Device", "Open Spotify on another device.")
                return
            if self.controller.is_paused:
                self.controller.sp.start_playback()
            else:
                self.controller.sp.start_playback(device_id=active_device['id'], uris=[uri])
            self.controller.is_paused = False
        except Exception as e:
            messagebox.showerror("Playback Error", str(e))

    def toggle_pause(self):
        try:
            if self.controller.is_paused:
                self.controller.sp.start_playback()
                self.controller.is_paused = False
            else:
                self.controller.sp.pause_playback()
                self.controller.is_paused = True
        except Exception as e:
            messagebox.showerror("Pause/Resume Error", str(e))

    def set_volume(self, val):
        try:
            if self.controller.sp:
                self.controller.sp.volume(int(val))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set volume:\n{e}")

    def next_track(self):
        if self.controller.track_index < len(self.controller.tracks) - 1:
            self.controller.track_index += 1
            self.update_track_display()

    def prev_track(self):
        if self.controller.track_index > 0:
            self.controller.track_index -= 1
            self.update_track_display()

# Entry point
if __name__ == '__main__':
    app = SpotifyApp()
    app.mainloop()
