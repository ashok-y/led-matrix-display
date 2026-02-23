import os
import time
import threading
import json
import importlib.util
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

class MatrixController:
    def __init__(self):
        # 1. Hardware Setup
        self.options = RGBMatrixOptions()
        self.options.rows = 32
        self.options.cols = 128
        self.options.gpio_slowdown = 4
        self.options.pwm_lsb_nanoseconds = 130
        self.options.hardware_mapping = 'adafruit-hat'
        self.options.drop_privileges = False
        
        self.matrix = RGBMatrix(options=self.options)
        self.canvas = self.matrix.CreateFrameCanvas()
        
        # 2. Fonts & Paths
        self.font = graphics.Font()
        self.small_font = graphics.Font()
        self.font.LoadFont("/fonts/7x13.bdf")
        self.small_font.LoadFont("/fonts/5x8.bdf")
        self.config_path = "/home/pi/workspace/led_matrix/config/config.json"
        
        # 3. Load Initial State
        self.config = self.load_config()
        self.apps = self.load_plugins()
        self.current_app_idx = 0

    def load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Config error: {e}")
            return {}

    def load_plugins(self):
        apps = []
        plugin_dir = "/home/pi/workspace/led_matrix/plugins"
        for str_file in os.listdir(plugin_dir):
            if str_file.endswith(".py") and str_file != "__init__.py":
                path = os.path.join(plugin_dir, str_file)
                module_name = f"plugin_{str_file[:-3]}"
                spec = importlib.util.spec_from_file_location(module_name, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                for name in dir(module):
                    obj = getattr(module, name)
                    if isinstance(obj, type) and hasattr(obj, 'render') and obj.__name__ != "MatrixApp":
                        # We pass 'self.config' to the app so it's reactive!
                        apps.append(obj(self.config)) 
        return apps

    def run(self):
        # Start background threads for each app's data updates
        for app in self.apps:
            threading.Thread(target=app.update, daemon=True).start()

        self.last_config_read = 0

        while True:
            # 1. REFRESH CONFIG & FIND VALID APP
            self.config.update(self.load_config())
            
            current_app = self.apps[self.current_app_idx]
            print(f"Current App: {current_app.__class__.__name__}")
            app_key_dict = {
                "dualclockapp": "clock",
                "weatherapp": "weather",
                "stocksapp": "stocks",
                "musicapp": "music"
             }
            app_key = app_key_dict.get(current_app.__class__.__name__.lower(), "")     
            
            # Check if current app is enabled
            app_cfg = self.config.get(app_key, {})
            enabled_status = self.config.get(app_key, {}).get('enabled')
            print(f"Checking App: {current_app.__class__.__name__} | Key: {app_key} | Enabled in JSON: {enabled_status}")
            if not app_cfg.get('enabled', True):
                print(f"Skipping {app_key} (disabled in config)")
                self.current_app_idx = (self.current_app_idx + 1) % len(self.apps)
                # If all apps are disabled, prevent high-speed looping
                time.sleep(1) 
                continue

            # 2. RUN PHASE (The active display time)
            print(f"Showing {app_key} for 30 seconds...")
            start_time = time.time()
            while time.time() - start_time < 30:
                # Refresh config every 1 second during the run to catch Web UI changes
                if time.time() - self.last_config_read > 1:
                    self.config.update(self.load_config())
                    self.last_config_read = time.time()

                # Re-check enabled status inside the loop for instant shut-off
                app_cfg = self.config.get(app_key, {})
                if not app_cfg.get('enabled', True):
                    print(f"App {app_key} was disabled while running. Breaking...")
                    break 

                self.canvas.Clear()
                # Render the app (ensure your plugins use self.config inside render!)
                current_app.render(self.canvas, self.font, self.small_font, y_offset=0)
                self.canvas = self.matrix.SwapOnVSync(self.canvas)
                time.sleep(0.016) # ~60 FPS

            # 3. SEARCH FOR THE NEXT ENABLED APP
            next_idx = (self.current_app_idx + 1) % len(self.apps)
            search_count = 0
            
            # Re-use your mapping dictionary here!
            app_key_map = {
                "dualclockapp": "clock",
                "weatherapp": "weather",
                "stocksapp": "stocks",
                "musicapp": "music"
            }

            while search_count < len(self.apps):
                candidate_app = self.apps[next_idx]
                # Use the map to get the key
                c_name = candidate_app.__class__.__name__.lower()
                candidate_key = app_key_map.get(c_name, "")
                
                # Check config using the correct key
                if self.config.get(candidate_key, {}).get('enabled', True):
                    break
                else:
                    print(f"Candidate {candidate_key} is disabled, skipping...")
                    next_idx = (next_idx + 1) % len(self.apps)
                    search_count += 1

            # 4. UPDATE INDEX
            self.current_app_idx = next_idx
            
if __name__ == "__main__":
    controller = MatrixController()
    controller.run()