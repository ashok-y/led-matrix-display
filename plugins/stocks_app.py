import time
import json
import yfinance as yf
from base_app import MatrixApp
from rgbmatrix import graphics

class StocksApp(MatrixApp):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.tickers = self.config.get("stocks", {}).get("symbols", [])
        self.data = {} # Ensure data dict is initialized
        
        # Animation State
        self.current_idx = 0
        self.next_idx = 1
        self.last_switch_time = time.time()
        self.is_transitioning = False
        self.local_push = 0

    def get_color(self, r, g, b):
        """Scales RGB values by the brightness config (0-255)."""
        brightness = int(self.config.get("brightness", 125))
        scale = brightness / 255.0
        return graphics.Color(int(r * scale), int(g * scale), int(b * scale))

    def update(self):
        """Background thread: Refresh data every 5 mins with conditional logging"""
        import traceback
        while True:
            debug = self.config.get("stocks", {}).get("debug", False)
            if debug:
                print("[StocksApp] Starting data refresh cycle...")
            for ticker in self.tickers:
                if debug:
                    print(f"[StocksApp] Fetching data for ticker: {ticker}")
                try:
                    t = yf.Ticker(ticker)
                    fast = t.fast_info
                    hist_df = t.history(period="1d", interval="15m")
                    price = fast['last_price']
                    prev_close = fast['previous_close']
                    history = hist_df['Close'].tolist() if not hist_df.empty else []
                    change = price - prev_close
                    pct = (change / prev_close) * 100 if prev_close != 0 else 0
                    self.data[ticker] = {
                        "price": f"${price:.2f}",
                        "move": f"{'+' if change >= 0 else ''}{change:.2f}",
                        "pct": f"{'+' if pct >= 0 else ''}{pct:.2f}%",
                        "history": history,
                        "up": change >= 0
                    }
                    if debug:
                        print(f"[StocksApp] Updated {ticker}: price={price}, prev_close={prev_close}, change={change}, pct={pct}")
                except Exception as e:
                    if debug:
                        print(f"[StocksApp] Fetch Error for {ticker}: {e}")
                        tb = traceback.format_exc()
                        print(f"[StocksApp] Traceback for {ticker}:\n{tb}")
                        # Check for rate/request limit in exception message
                        if any(word in str(e).lower() for word in ["rate limit", "request limit", "retry", "429"]):
                            print(f"[StocksApp] Rate/request limit likely hit for {ticker}. Exception: {e}")
                time.sleep(0.5)
            if debug:
                print("[StocksApp] Data refresh cycle complete. Sleeping for 5 minutes.")
            time.sleep(300)

    def render(self, canvas, font, small_font, y_offset=0):
        if not self.data: return

        # 1. Define Dynamic Colors
        white = self.get_color(255, 255, 255)
        green = self.get_color(0, 255, 0)
        red = self.get_color(255, 0, 0)

        now = time.time()
        
        # Transition Logic
        if not self.is_transitioning:
            if (now - self.last_switch_time) >= 6:
                if len(self.tickers) > 1:
                    self.is_transitioning = True
                    self.local_push = 0
                    self.next_idx = (self.current_idx + 1) % len(self.tickers)
                else:
                    self.last_switch_time = now

        if self.is_transitioning:
            self.local_push += 2 
            if self.local_push >= 32:
                self.current_idx = self.next_idx
                self.is_transitioning = False
                self.local_push = 0
                self.last_switch_time = now

        # Draw Frames
        display_indices = [self.current_idx, self.next_idx] if self.is_transitioning else [self.current_idx]
        
        for i, idx in enumerate(display_indices):
            sym = self.tickers[idx]
            if sym not in self.data: continue

            y_base = 0 if i == 0 else 32
            frame_y = y_offset + y_base - self.local_push
            
            d = self.data[sym]
            status_color = green if d['up'] else red
            
            # Symbol & Price (White)
            graphics.DrawText(canvas, font, 2, frame_y + 12, white, sym)
            graphics.DrawText(canvas, font, 2, frame_y + 26, white, d['price'])
            
            # UI Elements (Status Color)
            self.draw_arrow(canvas, 40, frame_y + 5, d['up'], status_color)
            graphics.DrawText(canvas, small_font, 45, frame_y + 11, status_color, d['move'])
            graphics.DrawText(canvas, small_font, 75, frame_y + 11, status_color, d['pct'])
            
            # Sparkline
            self.draw_sparkline(canvas, d['history'], frame_y, status_color)

    def draw_arrow(self, canv, x, y, is_up, color):
        size = 4
        if is_up:
            for i in range(size):
                graphics.DrawLine(canv, x - i, y + i, x + i, y + i, color)
        else:
            for i in range(size):
                graphics.DrawLine(canv, x - i, y + size - i, x + i, y + size - i, color)

    def draw_sparkline(self, canv, data, y_offset, color):
        if not data or len(data) < 2:
            return
        mn, mx = min(data), max(data)
        if mx == mn:
            y = y_offset + 16
            graphics.DrawLine(canv, 0, y, 127, y, color)
            return
        
        rng = mx - mn
        for i in range(len(data) - 1):
            x1 = int(i * (127 / (len(data)-1)))
            y1 = y_offset + 31 - int(((data[i] - mn) / rng) * 31)
            x2 = int((i+1) * (127 / (len(data)-1)))
            y2 = y_offset + 31 - int(((data[i+1] - mn) / rng) * 31)
            graphics.DrawLine(canv, x1, y1, x2, y2, color)