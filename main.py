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
        
        # Colors for status
        self.white = graphics.Color(255, 255, 255)
        self.blue = graphics.Color(0, 120, 255)

        # 3. Load Initial State
        self.show_loading_status("INITIALIZING...")
        self.config = self.load_config()
        self.apps = self.load_plugins()
        self.current_app_idx = 0
        self.last_config_read = 0

    def show_loading_status(self, message, sub_message="Please wait..."):
        """Displays a splash screen during startup/loading."""
        self.canvas.Clear()
        # Draw a simple blue border line
        graphics.DrawLine(self.canvas, 0, 0, 127, 0, self.blue)
        graphics.DrawText(self.canvas, self.font, 10, 14, self.white, message)
        graphics.DrawText(self.canvas, self.small_font, 10, 26, self.blue, sub_message)
        self.canvas = self.matrix.SwapOnVSync(self.canvas)

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
        files = [f for f in os.listdir(plugin_dir) if f.endswith(".py") and f != "__init__.py" and not f.startswith("m")]
        
        for str_file in files:
            app_name = str_file[:-3].upper()
            self.show_loading_status("LOADING PLUGINS", f"Plugin: {app_name}")
            
            path = os.path.join(plugin_dir, str_file)
            module_name = f"plugin_{str_file[:-3]}"
            spec = importlib.util.spec_from_file_location(module_name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and hasattr(obj, 'render') and obj.__name__ != "MatrixApp":
                    apps.append(obj(self.config)) 
        return apps

    def get_app_key(self, app_instance):
        """Helper to map Class Names to Config Keys."""
        mapping = {
            "dualclockapp": "clock",
            "weatherapp": "weather",
            "stocksapp": "stocks",
            "musicapp": "music"
        }
        return mapping.get(app_instance.__class__.__name__.lower(), "")

    def run(self):
        # Start background threads
        for app in self.apps:
            app_name = app.__class__.__name__
            self.show_loading_status("STARTING DATA", f"Thread: {app_name}")
            threading.Thread(target=app.update, daemon=True).start()

        self.show_loading_status("SYSTEM READY", "Starting loop...")
        time.sleep(1)

        while True:
            # 1. Refresh Config
            self.config.update(self.load_config())
            
            if not self.apps:
                self.show_loading_status("ERROR", "No Plugins Found")
                time.sleep(5)
                continue

            # 2. Validate Current App
            current_app = self.apps[self.current_app_idx]
            app_key = self.get_app_key(current_app)
            
            if not self.config.get(app_key, {}).get('enabled', True):
                print(f"Skipping {app_key} (disabled)")
                self.current_app_idx = (self.current_app_idx + 1) % len(self.apps)
                time.sleep(0.1)
                continue

            # 3. Execution Phase
            print(f"Displaying: {app_key}")
            start_time = time.time()
            while time.time() - start_time < 30:
                # Refresh config every 1s for instant responsiveness to Web UI
                if time.time() - self.last_config_read > 1:
                    self.config.update(self.load_config())
                    self.last_config_read = time.time()

                if not self.config.get(app_key, {}).get('enabled', True):
                    break # Exit immediately if disabled while running

                self.canvas.Clear()
                current_app.render(self.canvas, self.font, self.small_font, y_offset=0)
                self.canvas = self.matrix.SwapOnVSync(self.canvas)
                time.sleep(0.016)

            # 4. RESTORED: Find Next Enabled App
            next_idx = (self.current_app_idx + 1) % len(self.apps)
            search_count = 0
            
            while search_count < len(self.apps):
                candidate_app = self.apps[next_idx]
                candidate_key = self.get_app_key(candidate_app)
                
                if self.config.get(candidate_key, {}).get('enabled', True):
                    break
                else:
                    next_idx = (next_idx + 1) % len(self.apps)
                    search_count += 1

            self.current_app_idx = next_idx

if __name__ == "__main__":
    controller = MatrixController()
    controller.run()