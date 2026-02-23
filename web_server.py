from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)
CONFIG_FILE = "config/config.json"

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

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