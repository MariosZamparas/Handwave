🎵 HandWave

Έλεγχος μουσικής με χειρονομίες, μέσω Leap Motion.

🔍 Περιγραφή

Διαδραστικός music player που επιτρέπει:

- Αναπαραγωγή / παύση
- Αλλαγή τραγουδιού
- Ρύθμιση έντασης
  μέσω κινήσεων χεριού.

🛠️ Τεχνολογίες

- Python & OpenCV
- Webcam ή Leap Motion
- Spotify API
- PySide6 για μοντέρνο γραφικό περιβάλλον χρήστη
- Spotipy για επικοινωνία με το Spotify Web API
- Python-dotenv για φόρτωση μεταβλητών περιβάλλοντος
- Requests για λήψη εικόνων εξωφύλλου

📦 Εξαρτήσεις (Dependencies)

Εγκαταστήστε τις απαιτούμενες βιβλιοθήκες με:
```bash
pip install PySide6 spotipy python-dotenv requests
```

📄 Περιεχόμενο .env αρχείου (για πρόσβαση στο Spotify API):
```env
SPOTIPY_CLIENT_ID=your-client-id
SPOTIPY_CLIENT_SECRET=your-client-secret
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback
```

🎯 Στόχοι

- Hands-free έλεγχος μουσικής
- Βοηθητική τεχνολογία
