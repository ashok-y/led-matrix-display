import time
import random
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

# 1. Configuration
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 2
options.hardware_mapping = 'adafruit-hat'
options.gpio_slowdown = 2  # Keep this to prevent flickering
matrix = RGBMatrix(options = options)

# 2. Setup Rain Parameters
canvas = matrix.CreateFrameCanvas()
# Use a tiny font if possible, or just draw pixels/chars
font = graphics.Font()
# font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/4x6.bdf")
# The smallest font in your folder
font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/tom-thumb.bdf")

# List of characters to drop (Classic Matrix style)
chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ$+-*/=%\"#&_(),.;:?!\\|{}<>[]"

# Initialize column states: [current_y, speed]
# Canvas width is 128 (64 * 2)
columns = [ [random.randint(-32, 0), random.uniform(0.5, 1)] for _ in range(canvas.width // 4) ]

# Colors
green_bright = graphics.Color(100, 255, 100) # Head of the drop
green_dim = graphics.Color(0, 150, 0)        # Tail

try:
    print("Running Matrix Rain... Ctrl+C to stop.")
    while True:
        canvas.Clear()
        
        for i, (y, speed) in enumerate(columns):
            x = i * 4 # Space out columns
            
            # Draw the "trailing" characters (dimmer)
            for tail in range(1, 5):
                char = random.choice(chars)
                graphics.DrawText(canvas, font, x, int(y) - (tail * 6), green_dim, char)
            
            # Draw the "leading" character (brighter)
            char = random.choice(chars)
            graphics.DrawText(canvas, font, x, int(y), green_bright, char)
            
            # Advance the drop
            columns[i][0] += speed
            
            # Reset if it goes off screen
            if columns[i][0] > canvas.height + 30:
                columns[i][0] = random.randint(-20, 0)
                columns[i][1] = random.uniform(0.5, 1.5)

        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.05)

except KeyboardInterrupt:
    canvas.Clear()
    matrix.SwapOnVSync(canvas)