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
        
        # Load fonts once
        self.small_font = graphics.Font()
        self.small_font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/4x6.bdf")
        self.medium_font = graphics.Font()
        self.medium_font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/6x12.bdf")

        self.is_transitioning = False
        self.local_push = 0
        self.current_idx = 0
        self.next_idx = 0
        self.last_switch_time = time.time()

    def get_color(self, r, g, b):
        """Helper to scale any RGB color by the global brightness config."""
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
                        # Restore all data features
                        self.data[city]["description"] = response["weather"][0]["main"]
                        self.data[city]["temp"] = response["main"]["temp"]
                        self.data[city]["humidity"] = response["main"]["humidity"]
                        self.data[city]["wind"] = response["wind"]["speed"]
                        self.data[city]["sunrise"] = response["sys"]["sunrise"]
                        self.data[city]["sunset"] = response["sys"]["sunset"]
                        self.data[city]["timezone"] = response["timezone"]
                        self.data[city]["current_time"] = response["dt"]
                        
                        icon_code = response['weather'][0]['icon']
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
        if not self.data: return

        # 1. Setup Dynamic Colors
        white = self.get_color(255, 255, 255)
        temp_color = self.get_color(255, 165, 0) # Orange
        city_color = self.get_color(100, 100, 255) # Light Blue
        line_color = self.get_color(50, 50, 50)
        brightness_scale = int(self.config.get("brightness", 125)) / 255.0

        # 2. Transition Logic (64px slide)
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
            
            # --- Restored Time Calculations ---
            current_time = datetime.datetime.utcfromtimestamp(d.get("current_time", 0) + timezone_offset).strftime("%I:%M %p")
            sunset_dt = datetime.datetime.utcfromtimestamp(d.get("sunset", 0) + timezone_offset)
            sunset_time = sunset_dt.strftime("%I:%M %p")

            # --- SECTION 1: HEADER ---
            graphics.DrawText(canvas, self.small_font, 2, frame_y + 8, city_color, city_name[:12])
            graphics.DrawText(canvas, self.small_font, 80, frame_y + 8, white, current_time)
            graphics.DrawLine(canvas, 0, frame_y + 10, 127, frame_y + 10, line_color)

            # --- SECTION 2: ICON (with Brightness Scaling) ---
            if self.icons[city_name]:
                icon_img = self.icons[city_name]
                for y in range(32):
                    for x in range(32):
                        r, g, b = icon_img.getpixel((x, y))
                        if r > 30 or g > 30 or b > 30:
                            canvas.SetPixel(x - 5, y + frame_y + 12, int(r * brightness_scale), \
                                             int(g * brightness_scale), int(b * brightness_scale))

            # --- SECTION 3: CENTER (Temp & Desc) ---
            temp = d.get("temp", 0)
            temp_str = f"{int(temp)}F/{(temp - 32) * 5/9:.1f}C"
            graphics.DrawText(canvas, self.medium_font, 24, frame_y + 22, white, temp_str)
            graphics.DrawText(canvas, self.small_font, 24, frame_y + 32, city_color, d.get("description", "Clear"))

            # --- SECTION 4: FOOTER (Humidity, Wind, Sunset) ---
            graphics.DrawLine(canvas, 0, frame_y + 46, 127, frame_y + 46, line_color)
            hum_wind = f"{d.get('humidity')}% {int(d.get('wind'))}mph"
            graphics.DrawText(canvas, self.small_font, 80, frame_y + 18, temp_color, hum_wind)
            graphics.DrawText(canvas, self.small_font, 80, frame_y + 28, temp_color, f"SS:{sunset_time}")