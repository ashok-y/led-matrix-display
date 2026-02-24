import time
import json
import datetime
from rgbmatrix import graphics
from base_app import MatrixApp

class DualClockApp(MatrixApp):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.cities = self.config.get("clock", {}).get("cities", [])
        
        # Initialize colors once, but we will refresh them in render() 
        # in case brightness changes on the fly.
        self.update_colors()
        
        self.is_transitioning = False
        self.local_push = 0
        self.current_idx = 0
        self.next_idx = 0
        self.last_switch_time = time.time()
    
    def update_colors(self):
        """Calculates all colors relative to the brightness config."""
        b = int(self.config.get("brightness", 125))
        
        # Primary Colors
        self.white = graphics.Color(b, b, b)
        self.cyan = graphics.Color(0, b, b)
        
        # Adaptive Dim Colors (roughly 20-40% of max brightness)
        dim_val = max(20, int(b * 0.4)) 
        self.dim_gray = graphics.Color(dim_val, dim_val, dim_val)

    def get_city_time(self, offset):
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        return now_utc + datetime.timedelta(hours=offset)
    
    def draw_clock_pair(self, canvas, font, small_font, cities, y_pos):
        if len(cities) > 1:
            # Uses the dynamic dim_gray
            graphics.DrawLine(canvas, 64, y_pos + 4, 64, y_pos + 28, self.dim_gray)

        for i, city in enumerate(cities):
            x_start = 2 if i == 0 else 68
            city_time = self.get_city_time(city.get("offset", 0))
            
            # City Name (Cyan)
            graphics.DrawText(canvas, small_font, x_start, y_pos + 10, self.cyan, city.get("name", "Unknown")[:10])
            
            # Time and AM/PM (White)
            t_str = city_time.strftime("%I:%M")
            graphics.DrawText(canvas, font, x_start, y_pos + 26, self.white, t_str)
            graphics.DrawText(canvas, small_font, x_start + 46, y_pos + 26, self.white, city_time.strftime("%p")[0])

    def render(self, canvas, font, small_font, y_offset=0):
        now = time.time()
        
        # Refresh colors at the start of every render frame
        self.update_colors()

        num_cities = len(self.cities)
        num_pages = (num_cities + 1) // 2 

        if num_pages == 0:
            return

        # Transition Logic
        if not self.is_transitioning:
            if (now - self.last_switch_time) >= 6:
                if num_pages > 1:
                    self.is_transitioning = True
                    self.local_push = 0
                    self.next_idx = (self.current_idx + 1) % num_pages
                else:
                    self.last_switch_time = now

        if self.is_transitioning:
            self.local_push += 2 
            if self.local_push >= 32:
                self.current_idx = self.next_idx
                self.is_transitioning = False
                self.local_push = 0
                self.last_switch_time = now

        # Rendering
        display_indices = [self.current_idx, self.next_idx] if self.is_transitioning else [self.current_idx]
        
        for i, page_idx in enumerate(display_indices):
            y_base = 0 if i == 0 else 32
            frame_y = y_offset + y_base - self.local_push
            
            start_city = page_idx * 2
            end_city = start_city + 2
            current_pair = self.cities[start_city:end_city]
            
            self.draw_clock_pair(canvas, font, small_font, current_pair, frame_y)

        # Progress Bar (Cyan)
        sec_width = int((datetime.datetime.now().second / 60.0) * 128)
        graphics.DrawLine(canvas, 0, 31, sec_width, 31, self.cyan)