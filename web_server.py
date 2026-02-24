from flask import Flask, render_template, request, jsonify
import subprocess
import signal
import json
import os

app = Flask(__name__)
CONFIG_FILE = "config/config.json"
logging.basicConfig(level=logging.DEBUG)
# -------------------------
# CONFIG HELPERS
# -------------------------

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def get_sanitized_config():
    config = load_config()

    # Remove secrets safely
    if "music" in config:
        config["music"].pop("spotify_client_secret", None)
        config["music"].pop("spotify_access_token", None)
        config["music"].pop("refresh_token", None)

    if "web" in config:
        config["web"].pop("client_secret", None)

    if "weather" in config:
        config["weather"].pop("api_key", None)

    return config


# -------------------------
# MAIN PAGE
# -------------------------

@app.route('/')
def index():
    return render_template('index.html')


# -------------------------
# RETURN CONFIG (SANITIZED)
# -------------------------

@app.route('/config')
def get_config():
    return jsonify(get_sanitized_config())


# -------------------------
# POWER CONTROL
# -------------------------

MAIN_SCRIPT = "/home/pi/workspace/led_matrix/main.py"
VENV_PYTHON = "/home/pi/workspace/led_matrix/venv/bin/python"
PID_FILE = "/tmp/matrix.pid"

@app.route('/power', methods=['POST'])
def toggle_power():
    logging.debug(f"Starting process: {VENV_PYTHON} {MAIN_SCRIPT}")
    action = request.json.get('action')  # should be 'on' or 'off'
    if action not in ["on", "off"]:
        return jsonify({"status": "error", "message": "Invalid action"}), 400

    if action == 'off':
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                pid = int(f.read())
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            os.remove(PID_FILE)
        return jsonify({"status": "off"})

    elif action == 'on':
        if not os.path.exists(PID_FILE):
            process = subprocess.Popen(['sudo', VENV_PYTHON, MAIN_SCRIPT],
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)

            with open(PID_FILE, 'w') as f:
                f.write(str(process.pid))
        return jsonify({"status": "on"})


@app.route('/power-status', methods=['GET'])
def get_power_status():
    check = subprocess.run(["pgrep", "-f", "main.py"], capture_output=True)
    if check.returncode == 0:
        return jsonify({"status": "on"})
    return jsonify({"status": "off"})


# -------------------------
# UPDATE CONFIG
# -------------------------

@app.route('/update', methods=['POST'])
def update():
    data = request.json
    config = load_config()

    key = data.get('key')
    val = data.get('value')

    if not key:
        return jsonify({"status": "error", "message": "Missing key"}), 400

    # -------------------------
    # STOCK ADD
    # -------------------------

    if key == 'stocks.add_symbol':
        if not isinstance(val, str):
            return jsonify({"status": "error", "message": "Invalid symbol"}), 400

        symbol = val.strip().upper()

        if not symbol.isalnum() or len(symbol) > 10:
            return jsonify({"status": "error", "message": "Invalid symbol format"}), 400

        if symbol not in config['stocks']['symbols']:
            config['stocks']['symbols'].append(symbol)
            message = f"{symbol} added"
        else:
            message = f"{symbol} already exists"

        save_config(config)

        return jsonify({
            "status": "success",
            "message": message,
            "symbols": config['stocks']['symbols']
        })

    # -------------------------
    # STOCK REMOVE
    # -------------------------

    elif key == 'stocks.remove_symbol':
        if not isinstance(val, str):
            return jsonify({"status": "error", "message": "Invalid symbol"}), 400

        symbol = val.strip().upper()
        original_len = len(config['stocks']['symbols'])

        config['stocks']['symbols'] = [
            s for s in config['stocks']['symbols']
            if s != symbol
        ]

        if len(config['stocks']['symbols']) < original_len:
            message = f"{symbol} removed"
        else:
            message = f"{symbol} not found"

        save_config(config)

        return jsonify({
            "status": "success",
            "message": message,
            "symbols": config['stocks']['symbols']
        })

    # -------------------------
    # GENERAL UPDATES
    # -------------------------

    if 'brightness' in key:
        try:
            val = int(val)
            val = max(1, min(255, val))
        except (ValueError, TypeError):
            val = 100

    elif 'enabled' in key:
        if isinstance(val, str):
            val = val.lower() == 'true'

    elif 'update_interval' in key:
        try:
            val = int(val)
            val = max(10, val)
        except:
            val = 300

    # Handle nested keys
    if '.' in key:
        parent, child = key.split('.', 1)

        if parent not in config:
            config[parent] = {}

        config[parent][child] = val
    else:
        config[key] = val

    save_config(config)

    return jsonify({
        "status": "success",
        "saved_value": val,
        "type": type(val).__name__
    })


# -------------------------
# RUN APP
# -------------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)