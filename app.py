import json
import requests
import threading
import time
import websocket
import pyaudio

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# Exemple d'import, à adapter selon ton projet/config
from config import GLADIA_API_KEY, INIT_URL

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# -- Variables globales --
STOP_STREAMING = False
capture_thread = None
LOGS = []

# On stockera la config reçue du front ici
# Ex: { "encoding": "...", "sample_rate": 22050, ... }
user_config = {}

def initiate_session():
    global user_config

    default_config = {
        "encoding": "wav/pcm",
        "sample_rate": 16000,
        "bit_depth": 16,
        "channels": 1,
        "language_config": {
            "languages": ["fr"],
            "code_switching": False
        }
    }

    # On crée une copie de user_config, sans le champ "translate"
    user_config_filtered = dict(user_config)  # copie
    if "translate" in user_config_filtered:
        del user_config_filtered["translate"]

    config = {**default_config, **user_config_filtered}

    # Puis fusion language_config si besoin…
    if "language_config" in user_config_filtered:
        config["language_config"] = {
            **default_config["language_config"],
            **user_config_filtered["language_config"]
        }

    print("🎛️ Configuration transmise à Gladia:", config)

    headers = {"Content-Type": "application/json", "X-Gladia-Key": GLADIA_API_KEY}
    response = requests.post(INIT_URL, headers=headers, json=config)
    
    if response.ok:
        data = response.json()
        print("✅ Session initiée :", data)
        return data["id"], data["url"]
    else:
        print("❌ Erreur d'initiation :", response.status_code, response.text)
        return None, None


def on_message(ws, message):
    """
    Fonction callback appelée quand on reçoit un message de Gladia via WebSocket.
    """
    try:
        msg = json.loads(message)
        if msg.get("type") == "transcript":
            text = msg.get("data", {}).get("utterance", {}).get("text", "")
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            
            log_entry = f"[{timestamp}] {text}"
            LOGS.append(log_entry)

            # Émission temps réel vers le front via Socket.IO
            socketio.emit("new_transcript", {"log": log_entry})

            print(f"📝 {log_entry}")  # log en console serveur
    except Exception as e:
        print("⚠️ Erreur de traitement :", e)

def on_error(ws, error):
    """
    Gère les erreurs WebSocket.
    """
    print("❌ Erreur WebSocket :", error)

def on_close(ws, close_status_code, close_msg):
    """
    Gère la fermeture de la connexion WebSocket.
    """
    print("🔒 WebSocket fermé.")

def on_open(ws):
    """
    Dès l'ouverture de la connexion WebSocket, démarre le streaming audio local.
    """
    global STOP_STREAMING
    STOP_STREAMING = False
    
    print("🎤 Connexion WebSocket établie.")
    
    p = pyaudio.PyAudio()
    try:
        # On suppose que tu prends le micro par défaut (device_index=None)
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,  # Tu pourrais aussi lire ce rate depuis user_config si besoin
            input=True,
            frames_per_buffer=1024,
            input_device_index=None
        )  
    except Exception as e:
        print(f"❌ Erreur lors de l'ouverture du micro : {e}")
        return

    def run():
        """
        Boucle qui envoie en continu les paquets audio tant que STOP_STREAMING est False.
        """
        try:
            print("🎙️ Capture du micro en cours...")
            while not STOP_STREAMING:
                data = stream.read(4096, exception_on_overflow=False)
                ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
        except Exception as e:
            print("⚠️ Erreur lors de l'envoi du flux audio :", e)
        finally:
            print("🛑 Arrêt du streaming micro.")
            stream.stop_stream()
            stream.close()
            p.terminate()
            # On informe Gladia d'arrêter l'enregistrement
            ws.send(json.dumps({"type": "stop_recording"}))
            print("✅ Envoi terminé.")

    # Lance la boucle d'envoi audio dans un thread
    threading.Thread(target=run).start()

def start_capture():
    """
    Lance la session Gladia et la boucle WebSocket (bloquante).
    """
    session_id, ws_url = initiate_session()
    if not ws_url:
        print("❌ Impossible de démarrer la session Gladia.")
        return

    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # Boucle bloquante tant que le WebSocket est ouvert
    ws.run_forever()

### ROUTES FLASK ###

@app.route("/start-audio", methods=["POST"])
def start_audio():
    global capture_thread, STOP_STREAMING, user_config

    # Lecture de la config envoyée par le front
    posted_data = request.get_json() or {}
    user_config = posted_data  # On stocke directement l'objet JSON dans user_config

    # Si un thread est déjà en cours, on ne relance pas
    if capture_thread and capture_thread.is_alive():
        return jsonify({"message": "Capture déjà en cours"}), 400

    STOP_STREAMING = False

    # Lance la capture dans un thread
    capture_thread = threading.Thread(target=start_capture)
    capture_thread.start()

    return jsonify({"message": "Démarrage de la capture audio"}), 200

@app.route("/stop-audio", methods=["POST"])
def stop_audio():
    global STOP_STREAMING, capture_thread

    if not capture_thread or not capture_thread.is_alive():
        return jsonify({"message": "Aucune capture en cours"}), 400

    STOP_STREAMING = True
    return jsonify({"message": "Arrêt demandé"}), 200

@app.route("/logs", methods=["GET"])
def get_logs():
    """
    Renvoie tout l'historique de logs (transcriptions) au format JSON.
    (Pour ceux qui préfèrent récupérer l'historique en polling)
    """
    return jsonify(LOGS)

if __name__ == "__main__":
    # On lance le serveur avec SocketIO
    socketio.run(app, port=8000, debug=True)
