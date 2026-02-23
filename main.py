import os
import time
import threading
import sys
import importlib.util
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from base_app import MatrixApp

# --- Configuration & Hardware Setup ---
options = RGBMatrixOptions()
options.rows, options.cols, options.chain_length = 32, 64, 2
options.hardware_mapping = 'adafruit-hat'
matrix = RGBMatrix(options = options)
canvas = matrix.CreateFrameCanvas()

# --- Get the absolute path to this script's directory ---
base_dir = os.path.dirname(os.path.abspath(__file__))

# Build the path dynamically
font = graphics.Font()
small_font = graphics.Font()
font.LoadFont("/fonts/7x13.bdf")
small_font.LoadFont("/fonts/5x8.bdf")
# --- Dynamic Plugin Loader ---

def load_plugins():
    apps = []
    # Use the absolute path we verified exists
    plugin_dir = "/home/pi/workspace/led_matrix/plugins"
    
    for str_file in os.listdir(plugin_dir):
        # Your filter: starts with 'm', ends with '.py'
        if str_file.endswith(".py") and str_file != "__init__.py" and str_file.startswith("m"):
            path = os.path.join(plugin_dir, str_file)
            try:
                # Use a unique module name for each plugin
                module_name = f"plugin_{str_file[:-3]}"
                spec = importlib.util.spec_from_file_location(module_name, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                for name in dir(module):
                    obj = getattr(module, name)
                    # Robust check: Does it look like an App class?
                    if isinstance(obj, type) and hasattr(obj, 'render') and hasattr(obj, 'update'):
                        # Exclude the base class itself if it was imported into the module
                        if obj.__name__ != "MatrixApp":
                            print(f"Instantiating: {name} from {str_file}")
                            apps.append(obj())
                            
            except Exception as e:
                print(f"Error loading {str_file}: {e}")
                
    return apps

loaded_apps = load_plugins()
if not loaded_apps:
    print("No plugins loaded. Check your plugin directory and filenames.")
    sys.exit(1) # Stop the script gracefully
# Start background threads for each app
for app in loaded_apps:
    threading.Thread(target=app.update, daemon=True).start()

# --- Main Animation Loop ---
current_app_idx = 0
while True:
    current_app = loaded_apps[current_app_idx]
    next_app_idx = (current_app_idx + 1) % len(loaded_apps)
    next_app = loaded_apps[next_app_idx]

    # 1. RUN PHASE: Show current app and allow it to animate/update internally
    display_time = 30  # Increased so you can see multiple stocks
    start_time = time.time()
    while time.time() - start_time < display_time:
        canvas.Clear()
        # Call render with y_offset=0 because we are standing still
        current_app.render(canvas, font, small_font, y_offset=0)
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.016) 

    # 2. TRANSITION PHASE: Slide to the next Plugin
    for offset in range(0, 33, 2):
        canvas.Clear()
        current_app.render(canvas, font, small_font, y_offset=-offset)
        next_app.render(canvas, font, small_font, y_offset=32-offset)
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.02)

    current_app_idx = next_app_idx