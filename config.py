

import os
from dotenv import load_dotenv

# Charger les variables d'environnement (évite d'exposer ta clé API)
load_dotenv()

# 🔐 Remplace TA_CLE_API_HERE par ta vraie clé API dans un fichier .env

GLADIA_API_KEY = "3d0de7c8-df31-47c1-a157-7632652c8534"

# URL Gladia
INIT_URL = "https://api.gladia.io/v2/live"

# Fichier audio pour la transcription (wav/pcm 16kHz mono)
AUDIO_FILE_PATH = "sample_audio.wav"
