import time
import json
import yfinance as yf
from base_app import MatrixApp
from rgbmatrix import graphics

class StockApp(MatrixApp):
    def __init__(self,config):
        super().__init__()
        self.config = config

        self.tickers = self.config.get("stocks", {}).get("tickers", ["AAPL", "GOOGL", "AMZN", "META", "NFLX", "TSLA"])
        # Animation State
        self.current_idx = 0
        self.next_idx = 1
        self.offset = 0
        self.last_switch_time = time.time()
        self.is_transitioning = False
        self.local_push = 0
        self.brightness = self.config.get("brightness", 125)
        self.white = graphics.Color(self.brightness, self.brightness, self.brightness)
        self.green = graphics.Color(0, self.brightness, 0)
        self.red = graphics.Color(self.brightness, 0, 0)

    def update(self):
        """Background thread: Refresh data every 5 mins"""
        while True:
            for ticker in self.tickers:
                try:
                    t = yf.Ticker(ticker)
                    fast = t.fast_info
                    hist_df = t.history(period="1d", interval="15m")
                    
                    price = fast['last_price']
                    change = price - fast['previous_close']
                    
                    self.data[ticker] = {
                        "price": f"${price:.2f}",
                        "move": f"{'+' if change >= 0 else ''}{change:.2f}",
                        "pct": f"{abs((change / fast['previous_close']) * 100):.2f}%",
                        "history": hist_df['Close'].tolist() if not hist_df.empty else [],
                        "up": change >= 0
                    }
                except Exception as e:
                    print(f"Fetch Error {ticker}: {e}")
                time.sleep(0.5) # API Breathing room
            time.sleep(300)

    def render(self, canvas, font, small_font, y_offset=0):
        if not self.data: return
        
        now = time.time()
        
        # 1. Check if we need to START a transition
        if not self.is_transitioning:
            if (now - self.last_switch_time) >= 6:
                self.is_transitioning = True
                self.local_push = 0
                self.next_idx = (self.current_idx + 1) % len(self.tickers)

        # 2. Handle the local sliding animation
        if self.is_transitioning:
            self.local_push += 2 # Slide speed
            if self.local_push >= 32:
                self.current_idx = self.next_idx
                self.is_transitioning = False
                self.local_push = 0
                self.last_switch_time = now

        # 3. Draw the frames
        # We always draw the current one, and the next one only if we are sliding
        # This keeps the "slide up" effect active
        display_indices = [self.current_idx, self.next_idx] if self.is_transitioning else [self.current_idx]
        
        for i, idx in enumerate(display_indices):
            sym = self.tickers[idx]
            if sym not in self.data: continue

            # MATH: Combine the Engine's y_offset with our local sliding push
            # y_base: 0 for the outgoing stock, 32 for the incoming stock
            y_base = 0 if i == 0 else 32
            
            # The Magic Formula: 
            # Global Position + Frame Start Point - Local Sliding Animation
            frame_y = y_offset + y_base - self.local_push
            
            # --- Render Logic (Same as before) ---
            d = self.data[sym]
            status_color = self.green if d['up'] else self.red
            
            graphics.DrawText(canvas, font, 2, frame_y + 12, self.white, sym)
            graphics.DrawText(canvas, font, 2, frame_y + 26, self.white, d['price'])
            self.draw_arrow(canvas, 92, frame_y + 5, d['up'], status_color)
            graphics.DrawText(canvas, small_font, 100, frame_y + 11, status_color, d['pct'])
            graphics.DrawText(canvas, small_font, 55, frame_y + 11, status_color, d['move'])
            self.draw_sparkline(canvas, d['history'], frame_y, status_color)

    def draw_arrow(self, canv, x, y, is_up, color):
        if is_up:
            graphics.DrawLine(canv, x-2, y+4, x, y, color)
            graphics.DrawLine(canv, x, y, x+2, y+4, color)
            graphics.DrawLine(canv, x-2, y+4, x+2, y+4, color)
        else:
            graphics.DrawLine(canv, x-2, y, x, y+4, color)
            graphics.DrawLine(canv, x, y+4, x+2, y, color)
            graphics.DrawLine(canv, x-2, y, x+2, y, color)

    def draw_sparkline(self, canv, data, y_offset, color):
        if not data or len(data) < 2: return
        mn, mx = min(data), max(data)
        rng = mx - mn if mx != mn else 1
        for i in range(len(data) - 1):
            x1 = int(i * (127 / (len(data)-1)))
            y1 = (y_offset + 31) - int(((data[i] - mn) / rng) * 10)
            x2 = int((i+1) * (127 / (len(data)-1)))
            y2 = (y_offset + 31) - int(((data[i+1] - mn) / rng) * 10)
            graphics.DrawLine(canv, x1, y1, x2, y2, color)