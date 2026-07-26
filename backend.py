from flask import Flask, render_template
from flask_socketio import SocketIO
import zmq
import threading
import numpy as np
import atexit
import time

app = Flask(__name__, static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

context = zmq.Context()

# receptie date FFT de la GNU Radio
sub_socket = context.socket(zmq.SUB)
sub_socket.connect("tcp://127.0.0.1:5002")
sub_socket.setsockopt(zmq.SUBSCRIBE, b"")

# trimitere comenzi catre GNU Radio
cmd_socket = context.socket(zmq.PUB)
try:
    cmd_socket.bind("tcp://127.0.0.1:5555")
except zmq.ZMQError as e:
    print(f"[ZMQ Error] Nu se ooate face bind pe portul 5555: {e}", flush=True)
    print("[Sugestie] Inchide scripturile anterioare sau alege alt port.", flush=True)
    exit(1)

# variabile globale
current_freq = 2.441e9
current_sr = 20e6
latest_spectrum = None
spectrogram = []
MAX_SPECTROGRAM_ROWS = 100
expected_length = None
running = True


def receive_spectrum_data():
    global latest_spectrum, spectrogram, running, expected_length

    while running:
        try:
            data = sub_socket.recv()

            mag_linear = np.frombuffer(data, dtype=np.float32)
            if mag_linear.size == 0:
                continue

            if expected_length is None:
                expected_length = mag_linear.size

            elif mag_linear.size != expected_length:
                continue

            # conversie in dB
            mag_db = 20 * np.log10(mag_linear + 1e-6)

            if np.any(np.isnan(mag_db)) or np.any(np.isinf(mag_db)):
                continue

            # construire axa de frecventa
            freqs = np.linspace(
                current_freq - current_sr / 2,
                current_freq + current_sr / 2,
                len(mag_db)
            )

            # actualizare spectrograma
            spectrogram.append(mag_db.tolist())
            if len(spectrogram) > MAX_SPECTROGRAM_ROWS:
                spectrogram.pop(0)

            latest_spectrum = {
                "spectrum": mag_db.tolist(),
                "freqs": freqs.tolist(),
                "sample_rate": current_sr,
                "center_freq": current_freq
            }

            # emitere catre client
            socketio.emit("spectrum", latest_spectrum)
            socketio.emit("waterfall", {"line": spectrogram[-1]})
            print("[SocketIO] Spectru + linie waterfall transmise", flush=True)

            time.sleep(0.15)  # limitare rata de update pentru frontend

        except Exception as e:
            print(f"[ZMQ Error] {e}", flush=True)
            time.sleep(0.1)


@socketio.on("connect")
def on_connect():
    print("[SocketIO] Client conectat", flush=True)
    if latest_spectrum:
        socketio.emit("spectrum", latest_spectrum)
    if spectrogram:
        socketio.emit("waterfall", {"waterfall": spectrogram})


@socketio.on("update_parameters")
def handle_update(data):
    global current_freq, current_sr
    try:
        freq = float(data.get("frequency", current_freq))
        samp_rate = float(data.get("sample_rate", current_sr))
        gain = float(data.get("gain", 30))

        current_freq = freq
        current_sr = samp_rate

        cmd_socket.send_string(f"{freq},{samp_rate},{gain}\n")
        print(f"[ZMQ] Comenzi trimise: freq={freq}, sr={samp_rate}, gain={gain}", flush=True)

    except Exception as e:
        print(f"[SocketIO Error] {e}", flush=True)


@app.route("/")
def index():
    return render_template("index.html")


@atexit.register
def cleanup():
    global running
    running = False
    time.sleep(0.1)
    try: sub_socket.close()
    except: pass
    try: cmd_socket.close()
    except: pass
    try: context.term()
    except: pass


if __name__ == "__main__":
    print("[INFO] Serverul este pornit pe adresa http://localhost:5000", flush=True)
    threading.Thread(target=receive_spectrum_data, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False)

