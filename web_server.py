from flask import Flask, render_template, request, jsonify
import subprocess
import signal
import json
import os

app = Flask(__name__)
CONFIG_FILE = "config/config.json"

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

# Path to your main script and its PID file
MAIN_SCRIPT = "/home/pi/workspace/led_matrix/main.py"
VENV_PYTHON = "/home/pi/workspace/led_matrix/venv/bin/python"
PID_FILE = "/tmp/matrix.pid"

@app.route('/power', methods=['POST'])
def toggle_power():
    action = request.json.get('action') # 'on' or 'off'
    
    if action == 'off':
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                pid = int(f.read())
            try:
                # Kill the process group (sudo and its child)
                os.kill(pid, signal.SIGTERM)
                os.remove(PID_FILE)
                return jsonify({"status": "off"})
            except ProcessLookupError:
                os.remove(PID_FILE)
        return jsonify({"status": "already_off"})

    elif action == 'on':
        if not os.path.exists(PID_FILE):
            # Start main.py as a background process using sudo
            process = subprocess.Popen(['sudo', VENV_PYTHON, MAIN_SCRIPT], 
                                     stdout=subprocess.DEVNULL, 
                                     stderr=subprocess.DEVNULL)
            with open(PID_FILE, 'w') as f:
                f.write(str(process.pid))
            return jsonify({"status": "on"})
        return jsonify({"status": "already_on"})

@app.route('/')
def index():
    return render_template('index.html', config=load_config())

@app.route('/update', methods=['POST'])
def update():
    data = request.json
    config = load_config()
    
    key = data['key']
    val = data['value']

    # --- TYPE CONVERSION LOGIC ---
    # 1. Convert brightness to integer
    if 'brightness' in key:
        try:
            val = int(val)
        except (ValueError, TypeError):
            val = 100
            
    # 2. Ensure 'enabled' is a real boolean
    elif 'enabled' in key:
        if isinstance(val, str):
            val = val.lower() == 'true'
    # -----------------------------

    if '.' in key:
        parent, child = key.split('.')
        # Ensure the parent exists if you add new plugins later
        if parent not in config:
            config[parent] = {}
        config[parent][child] = val
    else:
        config[key] = val
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
        
    return jsonify({"status": "success", "saved_value": val, "type": type(val).__name__})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)