import time
import yfinance as yf
import threading
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
import os

import os
import certifi

# Force the certificate path to be readable by sudo
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

# Additional fix: some underlying libraries look here
if not os.path.exists('/etc/ssl/certs/ca-certificates.crt'):
    # If the system path is missing, link it to certifi
    os.environ['CURL_CA_BUNDLE'] = certifi.where()

# --- Matrix Setup ---
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 2
options.hardware_mapping = 'adafruit-hat'
options.gpio_slowdown = 2
matrix = RGBMatrix(options = options)
canvas = matrix.CreateFrameCanvas()

# --- Load Fonts ---
font = graphics.Font()
# We use a try/except block so the script tells us exactly what is wrong
# Define the path
font_path = "./rpi-rgb-led-matrix/fonts/7x13.bdf"


# 2. Try Loading
font = graphics.Font()
try:
    font.LoadFont(font_path)
    print("Font loaded successfully!")
except Exception as e:
    print(f"Font loading failed: {e}")

# --- Global Data Store ---
stock_data = {"text": "Loading Stocks...", "color": graphics.Color(0, 255, 0)}
UPDATE_INTERVAL = 300  # 5 minutes in seconds

def update_stocks():
    global stock_data
    tickers = ["AAPL", "TSLA", "NVDA", "BTC-USD"]
    while True:
        try:
            display_parts = []
            for symbol in tickers:
                t = yf.Ticker(symbol)
                # fast_info is quicker than regular info
                price = t.fast_info['last_price']
                change = price - t.fast_info['previous_close']
                pct = (change / t.fast_info['previous_close']) * 100
                
                arrow = "▲" if change >= 0 else "▼"
                display_parts.append(f"{symbol} {price:.2f} {arrow}{abs(pct):.1f}%")
            
            stock_data["text"] = "  |  ".join(display_parts)
            # Set color based on overall market (just an example, uses first ticker)
            stock_data["color"] = graphics.Color(0, 255, 0) # Green
            
        except Exception as e:
            print(f"Fetch error: {e}")
        
        time.sleep(UPDATE_INTERVAL)

# Start the background update thread
data_thread = threading.Thread(target=update_stocks, daemon=True)
data_thread.start()

# --- Main Animation Loop ---
pos = canvas.width
text_color = graphics.Color(0, 255, 255) # Cyan for readability

try:
    print("Running Dashboard... Updates every 5 mins.")
    while True:
        canvas.Clear()
        
        # Draw the scrolling text
        msg = stock_data["text"]
        # DrawText returns the length of the text drawn
        length = graphics.DrawText(canvas, font, pos, 22, text_color, msg)
        
        pos -= 1
        if (pos + length < 0):
            pos = canvas.width

        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.03)

except KeyboardInterrupt:
    pass