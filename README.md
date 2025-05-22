
# 🎵 HandWave

Έλεγχος Spotify με χειρονομίες και κάμερα — hands-free εμπειρία μουσικής.

---

## 🔍 Περιγραφή

Το **HandWave** είναι ένα διαδραστικό desktop app γραμμένο σε Python, που σας επιτρέπει να ελέγχετε την αναπαραγωγή μουσικής στο Spotify χρησιμοποιώντας **χειρονομίες μέσω κάμερας (Webcam)**.

---

## ✋ Υποστηριζόμενες Χειρονομίες

| Χειρονομία              | Ενέργεια                                              |
|--------------------------|--------------------------------------------------------|
| ✋ Ανοιχτή Παλάμη         | Αναπαραγωγή / Παύση (Play / Pause)                    |
| ➡️ Κίνηση Χεριού Δεξιά    | Επόμενο Τραγούδι (Next Track)                         |
| ⬅️ Κίνηση Χεριού Αριστερά | Προηγούμενο Τραγούδι (Previous Track)                |
| ⬆️ Κίνηση Χεριού Πάνω     | Αύξηση Έντασης κατά 10 (Volume +10)                  |
| ⬇️ Κίνηση Χεριού Κάτω     | Μείωση Έντασης κατά 10 (Volume -10)                  |

> ⚠️ Οι χειρονομίες γίνονται με **ένα χέρι**, μπροστά από την κάμερα. Το σύστημα διαθέτει μηχανισμό cooldown (~3 δευτ.) για αποφυγή πολλαπλών ενεργοποιήσεων.

---

## 🖥️ Περιβάλλον Εφαρμογής

- Spotify login (μέσω Spotipy)
- Προβολή λίστας αναπαραγωγής & τραγουδιών
- Πλήκτρα Play, Pause/Resume, Next, Previous
- Ένταση (slider)
- Προεπισκόπηση εξωφύλλου
- Ενσωματωμένη "κονσόλα" για εμφάνιση σφαλμάτων ή πληροφοριών

---

## 🛠️ Τεχνολογίες

- **Python 3.x**
- **MediaPipe** (για gesture recognition μέσω webcam)
- **OpenCV** (προβολή βίντεο & ανάλυση εικόνας)
- **Spotipy** (για Spotify Web API)
- **PySide6** (μοντέρνο GUI)
- **python-dotenv** (για .env με τα credentials)
- **requests** (λήψη εξωφύλλων)

---

## 📦 Πώς να το Τρέξετε

### ✅ Τρέξιμο από το `.exe` (Windows)

https://drive.google.com/file/d/14tHgzwWEe_gdp6HmFBHZqz0LeuogP2Nz/view?usp=sharing

1. Βάλτε τα εξής αρχεία **στον ίδιο φάκελο** με το `.exe`:
   - `style.qss` (προαιρετικό, για custom εμφάνιση)
   - `.env` αρχείο με τα Spotify API credentials

2. Διπλό κλικ στο `spotify_gui_pyside.exe`

---

### 🧑‍💻 Τρέξιμο από τον Κώδικα

1. Εγκαταστήστε τις εξαρτήσεις:

```bash
pip install PySide6 spotipy python-dotenv requests opencv-python mediapipe
```

2. Δημιουργήστε αρχείο `.env` με:

```env
SPOTIPY_CLIENT_ID=your-client-id
SPOTIPY_CLIENT_SECRET=your-client-secret
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback
```

3. Τρέξτε:

```bash
python spotify_gui_pyside.py
```

---

## 📌 Απαιτήσεις

- **Ενεργός λογαριασμός Spotify**
- **Spotify ανοιχτό σε τουλάχιστον μία συσκευή** (π.χ. κινητό, desktop app)

---

## 🎯 Στόχος

- Hands-free εμπειρία αναπαραγωγής μουσικής
- Ανάδειξη της αναγνώρισης χειρονομιών ως εναλλακτικό UI
- Μη εμπορική χρήση (demos, πειραματισμός, UX testing)

---

## ✍️ Δημιουργοί

Made with ❤️ by IEEE student branch ARTA
