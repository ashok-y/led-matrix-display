import io
import time
import requests
import json
from PIL import Image
from base_app import MatrixApp
from rgbmatrix import graphics
import datetime
from collections import defaultdict

class WeatherApp(MatrixApp):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.api_key = self.config.get("weather", {}).get("api_key", "")
        self.cities = self.config.get("weather", {}).get("cities", ["Cedar City"])
        
        self.data = defaultdict(defaultdict)
        self.icons = defaultdict(lambda: None)

        self.is_transitioning = False
        self.local_push = 0
        self.current_idx = 0
        self.next_idx = 0
        self.last_switch_time = time.time()

    def get_color(self, r, g, b):
        """Scales RGB values by the global brightness config."""
        brightness = int(self.config.get("brightness", 125))
        scale = brightness / 255.0
        return graphics.Color(int(r * scale), int(g * scale), int(b * scale))

    def update(self):
        """Background thread: Fetch weather every 15 minutes"""
        while True:
            try:
                for city in self.cities:
                    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units=imperial"
                    response = requests.get(url).json()
                    if response.get("main"):
                        weather_item = response["weather"][0]
                        self.data[city] = {
                            "description": weather_item["main"],
                            "temp": response["main"]["temp"],
                            "humidity": response["main"]["humidity"],
                            "wind": response["wind"]["speed"],
                            "sunset": response["sys"]["sunset"],
                            "timezone": response["timezone"],
                            "current_time": response["dt"]
                        }
                        
                        icon_code = weather_item['icon']
                        icon_url = f"http://openweathermap.org/img/wn/{icon_code}@2x.png"
                        img_res = requests.get(icon_url, stream=True)
                        img = Image.open(io.BytesIO(img_res.content)).convert('RGBA')
                        img = img.resize((32, 32), Image.NEAREST) 
                        
                        clean_bg = Image.new("RGB", (32, 32), (0, 0, 0))
                        clean_bg.paste(img, (0, 0), img) 
                        self.icons[city] = clean_bg
            except Exception as e:
                print(f"Weather Fetch Error: {e}")
            time.sleep(900)

    def render(self, canvas, font, small_font, y_offset=0):
        if not self.data:
            return

        # 1. Define Dynamic Colors
        white = self.get_color(255, 255, 255)
        temp_color = self.get_color(255, 165, 0)  # Orange
        city_color = self.get_color(100, 100, 255) # Light Blue
        dim_gray = self.get_color(50, 50, 50)
        
        brightness_scale = int(self.config.get("brightness", 125)) / 255.0

        # 2. Transition Logic
        now = time.time()
        if not self.is_transitioning:
            if (now - self.last_switch_time) >= 6:
                if len(self.cities) > 1:
                    self.is_transitioning = True
                    self.local_push = 0
                    self.next_idx = (self.current_idx + 1) % len(self.cities)
                else:
                    self.last_switch_time = now

        if self.is_transitioning:
            self.local_push += 4
            if self.local_push >= 64:
                self.current_idx = self.next_idx
                self.is_transitioning = False
                self.local_push = 0
                self.last_switch_time = now

        # 3. Drawing Loop
        display_indices = [self.current_idx, self.next_idx] if self.is_transitioning else [self.current_idx]
        
        for i, idx in enumerate(display_indices):
            city_name = self.cities[idx]
            if city_name not in self.data: continue
            
            y_base = 0 if i == 0 else 64
            frame_y = y_offset + y_base - self.local_push

            d = self.data[city_name]
            timezone_offset = d.get("timezone", 0)
            current_time = datetime.datetime.utcfromtimestamp(d.get("current_time", 0) + timezone_offset).strftime("%I:%M %p")
            sunset_time = datetime.datetime.utcfromtimestamp(d.get("sunset", 0) + timezone_offset).strftime("%I:%M %p")

            # Header
            graphics.DrawText(canvas, small_font, 2, frame_y + 8, city_color, city_name[:12])
            graphics.DrawText(canvas, small_font, 85, frame_y + 8, white, current_time)
            graphics.DrawLine(canvas, 0, frame_y + 10, 127, frame_y + 10, dim_gray)

            # Icon Rendering (with brightness scaling)
            if self.icons[city_name]:
                for y in range(32):
                    for x in range(32):
                        r, g, b = self.icons[city_name].getpixel((x, y))
                        if r > 10 or g > 10 or b > 10: # Only draw non-black pixels
                            canvas.SetPixel(x - 5, y + frame_y + 12, int(r * brightness_scale), int(g * brightness_scale), int(b * brightness_scale))

            # Temperature & Description
            temp = d.get("temp", 0)
            temp_str = f"{int(temp)}F/{(temp - 32) * 5/9:.1f}C"
            graphics.DrawText(canvas, font, 30, frame_y + 28, white, temp_str)
            graphics.DrawText(canvas, small_font, 30, frame_y + 38, city_color, d.get("description", "Clear"))

            # Footer Data
            graphics.DrawLine(canvas, 0, frame_y + 44, 127, frame_y + 44, dim_gray)
            hum_wind = f"H:{d.get('humidity')}% W:{int(d.get('wind'))}mph"
            graphics.DrawText(canvas, small_font, 5, frame_y