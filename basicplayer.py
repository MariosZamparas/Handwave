# File: spotify_login_gui.py

# GUI and media/image handling libraries
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import requests
import io

# Spotify integration
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# System utilities
import os
import sys

# Spotify API credentials (use your own from https://developer.spotify.com/dashboard)
CLIENT_ID = 'd04f33354a724aef88c5335713046cb3'
CLIENT_SECRET = 'dd7e99a0010442bdb113973b32324615'
REDIRECT_URI = 'http://localhost:8888/callback'

# Required permissions (scopes) for controlling playback
SCOPE = 'user-read-private user-read-email playlist-read-private user-modify-playback-state user-read-playback-state'


# Main application class inheriting from Tkinter root window
class SpotifyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Spotify Media Player")
        self.geometry("500x600")

        # Spotify client object (Spotipy), will be set after login
        self.sp = None
        self.tracks = []          # Track list from current playlist
        self.track_index = 0      # Index of currently selected track

        # Container to hold pages (frames)
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        # Page management: Landing and Playlist views
        self.frames = {}
        for F in (LandingPage, PlaylistPage):
            frame = F(self.container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Show landing page first
        self.show_frame(LandingPage)

    def show_frame(self, page):
        # Bring specified frame to the front
        frame = self.frames[page]
        frame.tkraise()

    def login(self):
        # Perform Spotify OAuth authentication and setup Spotipy client
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

            # Fetch user info after successful login
            user = self.sp.current_user()
            self.frames[LandingPage].update_user_info(user)

            # Preload playlists to save time when navigating
            self.frames[PlaylistPage].load_playlists()
        except Exception as e:
            messagebox.showerror("Login Failed", str(e))

    def logout(self):
        # Log out: clear token, reset state, and return to landing screen
        if os.path.exists(".cache"):
            os.remove(".cache")
        self.sp = None
        self.tracks = []
        self.track_index = 0
        self.frames[LandingPage].reset()
        self.frames[PlaylistPage].reset()
        self.show_frame(LandingPage)


# Landing screen with login/logout and basic user info
class LandingPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.label = tk.Label(self, text="Not logged in", font=("Arial", 14))
        self.label.pack(pady=20)

        self.login_btn = tk.Button(self, text="Log In with Spotify", command=self.controller.login)
        self.login_btn.pack(pady=5)

        self.logout_btn = tk.Button(self, text="Log Out", command=self.controller.logout)
        self.logout_btn.pack(pady=5)
        self.logout_btn.config(state="disabled")

        self.goto_player_btn = tk.Button(self, text="Go to Player", command=lambda: controller.show_frame(PlaylistPage))
        self.goto_player_btn.pack(pady=5)
        self.goto_player_btn.config(state="disabled")

    def update_user_info(self, user):
        # After login, show user info and enable buttons
        name = user.get('display_name', 'Unknown')
        email = user.get('email', 'N/A')
        self.label.config(text=f"Welcome {name}\nEmail: {email}")
        self.login_btn.config(state="disabled")
        self.logout_btn.config(state="normal")
        self.goto_player_btn.config(state="normal")

    def reset(self):
        # Reset UI when user logs out
        self.label.config(text="Not logged in")
        self.login_btn.config(state="normal")
        self.logout_btn.config(state="disabled")
        self.goto_player_btn.config(state="disabled")


# Playlist selection and playback interface
class PlaylistPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Playlist listbox
        self.playlist_box = tk.Listbox(self, width=50)
        self.playlist_box.pack(pady=10)
        self.playlist_box.bind("<<ListboxSelect>>", self.load_tracks)

        # Currently selected track
        self.track_label = tk.Label(self, text="No track loaded", wraplength=480)
        self.track_label.pack(pady=5)

        # Album cover preview
        self.cover_canvas = tk.Label(self)
        self.cover_canvas.pack(pady=10)

        # Playback control buttons
        controls = tk.Frame(self)
        controls.pack(pady=10)
        tk.Button(controls, text="Play", command=self.play_track).grid(row=0, column=0, padx=5)
        tk.Button(controls, text="Pause", command=self.pause_track).grid(row=0, column=1, padx=5)
        tk.Button(controls, text="Back", command=self.prev_track).grid(row=0, column=2, padx=5)
        tk.Button(controls, text="Next", command=self.next_track).grid(row=0, column=3, padx=5)

        # Volume slider
        volume_frame = tk.Frame(self)
        volume_frame.pack(pady=10)
        tk.Label(volume_frame, text="Volume").pack()
        self.volume_slider = tk.Scale(volume_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.set_volume)
        self.volume_slider.set(50)
        self.volume_slider.pack()

        # Back navigation to landing screen
        self.back_btn = tk.Button(self, text="Back to Home", command=lambda: controller.show_frame(LandingPage))
        self.back_btn.pack(pady=5)

    def reset(self):
        # Reset state when user logs out
        self.playlist_box.delete(0, tk.END)
        self.track_label.config(text="No track loaded")
        self.cover_canvas.config(image='')
        self.controller.tracks = []
        self.controller.track_index = 0

    def load_playlists(self):
        # Load all user playlists from Spotify
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
        # Load tracks when user selects a playlist
        if not self.controller.sp:
            return
        try:
            selection = event.widget.curselection()
            if not selection:
                return
            index = selection[0]
            playlist_id = self.playlist_data[index]['id']
            results = self.controller.sp.playlist_items(playlist_id)
            self.controller.tracks = [item['track'] for item in results['items'] if item.get('track')]
            self.controller.track_index = 0
            self.update_track_display()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load tracks:\n{e}")

    def update_track_display(self):
        # Show selected track details and album art
        if not self.controller.tracks:
            self.track_label.config(text="No tracks available.")
            return
        track = self.controller.tracks[self.controller.track_index]
        name = track['name']
        artist = track['artists'][0]['name']
        self.track_label.config(text=f"{name} by {artist}")
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
        # Start playback of current track on user's active device
        try:
            track = self.controller.tracks[self.controller.track_index]
            uri = track['uri']
            devices = self.controller.sp.devices()
            active_device = next((d for d in devices['devices'] if d['is_active']), None)
            if not active_device:
                messagebox.showerror("No Active Device", "Open Spotify on another device.")
                return
            self.controller.sp.start_playback(device_id=active_device['id'], uris=[uri])
        except Exception as e:
            messagebox.showerror("Playback Error", str(e))

    def pause_track(self):
        # Pause current playback
        try:
            self.controller.sp.pause_playback()
        except Exception as e:
            messagebox.showerror("Pause Error", str(e))

    def set_volume(self, val):
        # Adjust Spotify volume (0–100)
        try:
            if self.controller.sp:
                self.controller.sp.volume(int(val))
            else:
                messagebox.showerror("Spotify Error", "You're not logged in.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set volume:\n{e}")

    def next_track(self):
        # Move to the next track in the list
        if self.controller.track_index < len(self.controller.tracks) - 1:
            self.controller.track_index += 1
            self.update_track_display()

    def prev_track(self):
        # Move to the previous track
        if self.controller.track_index > 0:
            self.controller.track_index -= 1
            self.update_track_display()


# Entry point
if __name__ == '__main__':
    app = SpotifyApp()
    app.mainloop()
