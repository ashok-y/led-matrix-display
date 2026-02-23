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
    
    # Handle nested keys like 'plugins.spotify'
    key = data['key']
    if '.' in key:
        parent, child = key.split('.')
        config[parent][child] = data['value']
    else:
        config[key] = data['value']
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
        
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)