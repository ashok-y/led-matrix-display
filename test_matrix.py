import os
import time
import threading
import certifi
import yfinance as yf
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

# --- SSL & Environment ---
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

# --- Matrix Setup ---
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 2
options.hardware_mapping = 'adafruit-hat'
options.gpio_slowdown = 2
matrix = RGBMatrix(options = options)
canvas = matrix.CreateFrameCanvas()

# --- Fonts ---
font = graphics.Font()
font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/7x13.bdf") 
small_font = graphics.Font()
small_font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/5x8.bdf") 

# --- Watchlist ---
ticker_list = [
    "PL", "NVO", "BROS", "AMD", "WMT", "INTC", "WM", "LLY", "PYPL", "AVGO",
    "MSFT", "COST", "HIMS", "TSLA", "HOOD", "V", "TGT", "ASML", "NVDA", "SPOT",
    "SMH", "META", "DUOL", "NFLX", "SHOP", "RDDT", "AMZN", "TSM", "GOOGL", "CELH"
]

stock_data = {} 
current_index = 0

def fetch_all_stocks():
    global stock_data
    while True:
        for symbol in ticker_list:
            try:
                t = yf.Ticker(symbol)
                fast = t.fast_info
                price = fast['last_price']
                change_amt = price - fast['previous_close']
                pct = (change_amt / fast['previous_close']) * 100
                
                hist_df = t.history(period="1d", interval="15m")
                hist = hist_df['Close'].tolist() if not hist_df.empty else []
                
                stock_data[symbol] = {
                    "price": f"${price:.2f}",
                    "move": f"{'+' if change_amt >= 0 else ''}{change_amt:.2f}",
                    "pct": f"{abs(pct):.2f}%",
                    "history": hist,
                    "up": change_amt >= 0
                }
            except Exception as e:
                print(f"Fetch Error {symbol}: {e}")
            time.sleep(0.5) 
        time.sleep(300)

threading.Thread(target=fetch_all_stocks, daemon=True).start()

# --- Synced Drawing Helpers ---
def draw_arrow(canv, x, y, is_up, color):
    """Draws a sharp 5-pixel tall arrow in the specified color"""
    if is_up:
        # Solid up triangle
        graphics.DrawLine(canv, x-2, y+4, x, y, color)
        graphics.DrawLine(canv, x, y, x+2, y+4, color)
        graphics.DrawLine(canv, x-2, y+4, x+2, y+4, color)
        for i in range(1, 4):
            graphics.DrawLine(canv, x-2+i, y+4-i, x+2-i, y+4-i, color)
    else:
        # Solid down triangle
        graphics.DrawLine(canv, x-2, y, x, y+4, color)
        graphics.DrawLine(canv, x, y+4, x+2, y, color)
        graphics.DrawLine(canv, x-2, y, x+2, y, color)
        for i in range(1, 4):
            graphics.DrawLine(canv, x-2+i, y+i, x+2-i, y+i, color)

def draw_sparkline(canv, data, y_offset, color):
    """Draws the 1-day trend line in the specified color"""
    if not data or len(data) < 2: return
    mn, mx = min(data), max(data)
    rng = mx - mn if mx != mn else 1
    for i in range(len(data) - 1):
        x1 = int(i * (127 / (len(data)-1)))
        y1 = (y_offset + 31) - int(((data[i] - mn) / rng) * 10)
        x2 = int((i+1) * (127 / (len(data)-1)))
        y2 = (y_offset + 31) - int(((data[i+1] - mn) / rng) * 10)
        graphics.DrawLine(canv, x1, y1, x2, y2, color)

# --- Animation Colors ---
white = graphics.Color(255, 255, 255)
green = graphics.Color(0, 255, 0)
red = graphics.Color(255, 0, 0)

try:
    while True:
        if ticker_list[current_index] not in stock_data:
            time.sleep(1)
            continue

        next_index = (current_index + 1) % len(ticker_list)
        time.sleep(6) # View for 6 seconds

        # The Vertical Slide Transition
        for offset in range(0, 33, 2):
            canvas.Clear()
            
            for i, idx in enumerate([current_index, next_index]):
                y_base = 0 if i == 0 else 32
                frame_y = y_base - offset
                
                sym = ticker_list[idx]
                if sym in stock_data:
                    d = stock_data[sym]
                    # THE SYNCED COLOR LOGIC
                    status_color = green if d['up'] else red
                    
                    # Top line: Symbol (White) | Arrow + Pct (Synced Color)
                    graphics.DrawText(canvas, font, 2, frame_y + 12, white, sym)
                    draw_arrow(canvas, 92, frame_y + 5, d['up'], status_color)
                    graphics.DrawText(canvas, small_font, 100, frame_y + 11, status_color, d['pct'])
                    
                    # Mid line: Price (White) | Dollar Move (Synced Color)
                    graphics.DrawText(canvas, font, 2, frame_y + 26, white, d['price'])
                    graphics.DrawText(canvas, small_font, 85, frame_y + 25, status_color, d['move'])
                    
                    # Bottom line: Sparkline (Synced Color)
                    draw_sparkline(canvas, d['history'], frame_y, status_color)

            canvas = matrix.SwapOnVSync(canvas)
            time.sleep(0.01)

        current_index = next_index

except KeyboardInterrupt:
    print("System Shutdown.")