import json
import requests
import threading
import time
import websocket
import wave
from config import GLADIA_API_KEY, INIT_URL, AUDIO_FILE_PATH

def initiate_session():
    """Initie une session Gladia et récupère l'URL WebSocket."""
    config = {
        "encoding": "wav/pcm",
        "sample_rate": 16000,
        "bit_depth": 16,
        "channels": 1,
    }
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
    """Affiche la transcription en direct avec timestamps."""
    try:
        msg = json.loads(message)
        if msg.get("type") == "transcript":
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            print(f"📝 [{timestamp}] {msg['data']['utterance']['text']}")
    except Exception as e:
        print("⚠️ Erreur de traitement :", e)

def on_error(ws, error):
    """Gestion des erreurs WebSocket."""
    print("❌ Erreur WebSocket :", error)

def on_close(ws, close_status_code, close_msg):
    """Fermeture propre de la connexion WebSocket."""
    print("🔒 WebSocket fermé.")

def on_open(ws):
    """Envoie un fichier audio .wav à Gladia en petits morceaux."""
    print("🎤 Connexion WebSocket établie.")

    def run():
        try:
            with wave.open(AUDIO_FILE_PATH, "rb") as wf:
                chunk_size = 4096  # Taille des morceaux envoyés
                while chunk := wf.readframes(chunk_size):
                    ws.send(chunk, opcode=websocket.ABNF.OPCODE_BINARY)
                    time.sleep(0.1)  # Simule un envoi progressif

            ws.send(json.dumps({"type": "stop_recording"}))
            print("✅ Envoi terminé.")

        except Exception as e:
            print("⚠️ Erreur d'envoi audio :", e)

    threading.Thread(target=run).start()

def main():
    session_id, ws_url = initiate_session()
    if not ws_url:
        return

    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    ws.run_forever()

if __name__ == "__main__":
    main()
