import json
import requests
import threading
import time
import websocket
import pyaudio
from config import GLADIA_API_KEY, INIT_URL


def initiate_session():
    """
    Initie une session Gladia en temps réel et récupère l'URL WebSocket.
    Seuls les paramètres de configuration supportés par l'API live sont utilisés.
    """
    # Pour l'API en temps réel, seuls les paramètres liés au format audio sont acceptés.
    config = {
        "encoding": "wav/pcm",
        "sample_rate": 16000,
        "bit_depth": 16,
        "channels": 1,
        "language_config": {
            "languages": ["fr"],  # Spécifie la langue souhaitée (par exemple, anglais)
            "code_switching": False
        }
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

last_text = None  # variable globale ou dans un scope accessible

def on_message(ws, message):
    global last_text
    try:
        msg = json.loads(message)
        if msg.get("type") == "transcript":
            text = msg.get("data", {}).get("utterance", {}).get("text", "")
            
            # Empêcher les doublons exacts
            if text and text != last_text:
                timestamp = time.strftime("%H:%M:%S", time.localtime())
                print(f"📝 [{timestamp}] {text}")
                last_text = text

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

def get_microphone_index():
    """
    Liste les microphones disponibles et demande à l'utilisateur de choisir.
    Retourne l'index du micro choisi ou None si aucun micro valide n'est détecté.
    """
    p = pyaudio.PyAudio()
    device_index = None
    input_devices = []
    
    print("\n🔍 Liste des microphones détectés :")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        # On considère comme micro tout périphérique ayant au moins une entrée audio
        if info["maxInputChannels"] > 0:
            input_devices.append((i, info["name"], info["defaultSampleRate"]))
            print(f"🎤 {i}: {info['name']} (SampleRate: {info['defaultSampleRate']})")
    
    p.terminate()
    
    if not input_devices:
        print("\n❌ Aucun micro détecté !")
        return None
    
    try:
        selected_index = int(input("\n🎙️ Entrez le numéro du micro à utiliser : "))
        if any(selected_index == d[0] for d in input_devices):
            device_index = selected_index
            for d in input_devices:
                if d[0] == selected_index:
                    print(f"\n✅ Micro sélectionné : {d[1]} (Index {d[0]})")
                    break
        else:
            print("\n❌ Numéro invalide !")
            return None
    except ValueError:
        print("\n❌ Entrée invalide !")
        return None

    return device_index

def on_open(ws):
    """
    Dès l'ouverture de la connexion WebSocket, démarre le streaming audio depuis le micro.
    Le flux audio est lu avec PyAudio et envoyé en binaire au WebSocket.
    """
    print("🎤 Connexion WebSocket établie.")
    
    device_index = get_microphone_index()
    if device_index is None:
        print("❌ Impossible d'utiliser le micro !")
        return
    
    p = pyaudio.PyAudio()
    try:
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=16000,
                        input=True,
                        frames_per_buffer=1024,
                        input_device_index=device_index)
    except Exception as e:
        print(f"❌ Erreur lors de l'ouverture du micro : {e}")
        return

    def run():
        try:
            print("🎙️ Capture du micro en cours...")
            while True:
                data = stream.read(4096, exception_on_overflow=False)
                ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
        except KeyboardInterrupt:
            print("🛑 Arrêt du streaming micro (KeyboardInterrupt).")
        except Exception as e:
            print("⚠️ Erreur lors de l'envoi du flux audio :", e)
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
            ws.send(json.dumps({"type": "stop_recording"}))
            print("✅ Envoi terminé.")

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
