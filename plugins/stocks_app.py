import time
import json
import yfinance as yf
from base_app import MatrixApp
from rgbmatrix import graphics

class StocksApp(MatrixApp):
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
        

    def update(self):
        """Background thread: Refresh data every 5 mins"""
        while True:
            for ticker in self.tickers:
                try:
                    t = yf.Ticker(ticker)
                    fast = t.fast_info
                    hist_df = t.history(period="1d", interval="15m")
                    price = fast['last_price']
                    prev_close = fast['previous_close']
                    history = hist_df['Close'].tolist() if not hist_df.empty else []
                    # Always use last price and previous close for change and pct
                    change = price - prev_close
                    pct = (change / prev_close) * 100 if prev_close != 0 else 0
                    self.data[ticker] = {
                        "price": f"${price:.2f}",
                        "move": f"{'+' if change >= 0 else ''}{change:.2f}",
                        "pct": f"{'+' if pct >= 0 else ''}{pct:.2f}%",
                        "history": history,
                        "up": change >= 0
                    }
                except Exception as e:
                    print(f"Fetch Error {ticker}: {e}")
                time.sleep(0.5) # API Breathing room
            time.sleep(300)

    def render(self, canvas, font, small_font, y_offset=0):
        if not self.data: return

        self.brightness = self.config.get("brightness", 125)
        self.white = graphics.Color(self.brightness, self.brightness, self.brightness)
        self.green = graphics.Color(0, self.brightness, 0)
        self.red = graphics.Color(self.brightness, 0, 0)

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
            # Symbol
            graphics.DrawText(canvas, font, 2, frame_y + 12, self.white, sym)
            # Price
            graphics.DrawText(canvas, font, 2, frame_y + 26, self.white, d['price'])
            
            # Arrow
            self.draw_arrow(canvas, 40, frame_y + 5, d['up'], status_color)
            # Percentage and Change
            graphics.DrawText(canvas, small_font, 45, frame_y + 11, status_color, d['move'])
            graphics.DrawText(canvas, small_font, 75, frame_y + 11, status_color, d['pct'])
            self.draw_sparkline(canvas, d['history'], frame_y, status_color)

    def draw_arrow(self, canv, x, y, is_up, color):
        # Draw a solid triangle up or down
        size = 4
        if is_up:
            # Upward solid triangle
            for i in range(size):
                graphics.DrawLine(canv, x - i, y + i, x + i, y + i, color)
        else:
            # Downward solid triangle
            for i in range(size):
                graphics.DrawLine(canv, x - i, y + size - i, x + i, y + size - i, color)


    def draw_sparkline(self, canv, data, y_offset, color):
        if not data or len(data) < 2:
            return
        mn, mx = min(data), max(data)
        # If all values are the same, draw a flat line in the middle
        if mx == mn:
            y = y_offset + 16
            graphics.DrawLine(canv, 0, y, 127, y, color)
            return
        rng = mx - mn
        for i in range(len(data) - 1):
            x1 = int(i * (127 / (len(data)-1)))
            # Use full 32-pixel height
            y1 = y_offset + 31 - int(((data[i] - mn) / rng) * 31)
            x2 = int((i+1) * (127 / (len(data)-1)))
            y2 = y_offset + 31 - int(((data[i+1] - mn) / rng) * 31)
            graphics.DrawLine(canv, x1, y1, x2, y2, color)