import time
import json
import datetime
from rgbmatrix import graphics
from base_app import MatrixApp

class DualClockApp(MatrixApp):
    def __init__(self,config):
        super().__init__()
        # Configure your cities and their UTC offsets here
        self.config = config
        self.cities = self.config.get("clock", {}).get("cities", [])
        self.brightness = self.config.get("brightness", 125)
        self.white = graphics.Color(self.brightness, self.brightness, self.brightness)
        self.cyan = graphics.Color(0, self.brightness, self.brightness)
        self.dim_gray = graphics.Color(50, 50, 50)
        self.is_transitioning = False
        self.local_push = 0
        self.current_idx = 0
        self.next_idx = 0
        self.last_switch_time = time.time()
    
    def get_city_time(self, offset):
        # Calculate time based on UTC offset
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        city_time = now_utc + datetime.timedelta(hours=offset)
        return city_time
    
    def draw_clock_pair(self, canvas, font, small_font, cities, y_pos):
        # Only draw the divider if there is actually a second city in this pair
        if len(cities) > 1:
            graphics.DrawLine(canvas, 64, y_pos + 4, 64, y_pos + 28, self.dim_gray)

        for i, city in enumerate(cities):
            x_start = 2 if i == 0 else 68
            # In your config, cities should look like: {"name": "Guntur", "offset": 5.5}
            city_time = self.get_city_time(city.get("offset", 0))
            
            graphics.DrawText(canvas, small_font, x_start, y_pos + 10, self.cyan, city.get("name", "Unknown")[:10])
            t_str = city_time.strftime("%I:%M")
            graphics.DrawText(canvas, font, x_start, y_pos + 26, self.white, t_str)
            graphics.DrawText(canvas, small_font, x_start + 46, y_pos + 26, self.white, city_time.strftime("%p")[0])

    def update(self):
        """No background data fetching needed for clock, but we could add features here later."""
        while True:
            time.sleep(1)  # Just sleep, all work is done in render

    def render(self, canvas, font, small_font, y_offset=0):
        now = time.time()
        self.brightness = int(self.config.get("brightness", 125))
        self.white = graphics.Color(self.brightness, self.brightness, self.brightness)
        # Calculate how many "pages" (pairs) we have
        # Using math.ceil for odd numbers of cities
        num_cities = len(self.cities)
        num_pages = (num_cities + 1) // 2 

        if num_pages == 0:
            return

        # 1. Transition Logic
        if not self.is_transitioning:
            if (now - self.last_switch_time) >= 6:
                if num_pages > 1: # Only transition if we have more than one pair
                    self.is_transitioning = True
                    self.local_push = 0
                    self.next_idx = (self.current_idx + 1) % num_pages
                else:
                    self.last_switch_time = now # Reset timer if only one page

        if self.is_transitioning:
            self.local_push += 2 
            if self.local_push >= 32:
                self.current_idx = self.next_idx
                self.is_transitioning = False
                self.local_push = 0
                self.last_switch_time = now

        # 2. Rendering
        display_indices = [self.current_idx, self.next_idx] if self.is_transitioning else [self.current_idx]
        
        for i, page_idx in enumerate(display_indices):
            y_base = 0 if i == 0 else 32
            frame_y = y_offset + y_base - self.local_push
            
            # Slice the flat list to get the pair for this "page"
            start_city = page_idx * 2
            end_city = start_city + 2
            current_pair = self.cities[start_city:end_city]
            
            self.draw_clock_pair(canvas, font, small_font, current_pair, frame_y)

        # 3. Static Progress Bar
        sec_width = int((datetime.datetime.now().second / 60.0) * 128)
        graphics.DrawLine(canvas, 0, 31, sec_width, 31, self.cyan)