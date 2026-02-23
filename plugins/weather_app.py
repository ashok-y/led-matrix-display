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
    def __init__(self):
        super().__init__()
        self.config = json.load(open("./config/config.json"))
        self.api_key = self.config.get("weather", {}).get("api_key", "")
        if self.api_key == "":
            print("Warning: No API key found for WeatherApp. Please add it to config.json.")
        self.city = self.config.get("weather", {}).get("city", "Cedar City") # Change this to your city
        
        self.cities = self.config.get("weather", {}).get("cities", ["Cedar City"])

        self.brightness = self.config.get("brightness", 125)
        # Colors
        self.temp_color = graphics.Color(self.brightness, 165, 0) # Orange
        self.city_color = graphics.Color(100, 100, self.brightness) # Light Blue
        self.white = graphics.Color(self.brightness, self.brightness, self.brightness)
        
        self.data = defaultdict(defaultdict) # city -> weather data dict
        self.icons = defaultdict(lambda: None) # city -> processed PIL Image for icon
        self.font = graphics.Font()
        self.font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/6x13.bdf")
        self.small_font = graphics.Font()
        self.small_font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/4x6.bdf")
        self.medium_font = graphics.Font()
        self.medium_font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/6x12.bdf")

        self.is_transitioning = False
        self.local_push = 0
        self.current_idx = 0
        self.next_idx = 0
        self.last_switch_time = time.time()
    
    def update(self):
        """Background thread: Fetch weather every 15 minutes"""
        while True:
            try:
                for city in self.cities:
                    print(f"Fetching weather for {city}...")
                    # units=imperial for Fahrenheit, units=metric for Celsius
                    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units=imperial"
                    response = requests.get(url).json()
                    if response.get("main"):
                        # Assuming 'res' is your JSON response dictionary
                        if "weather" in response and len(response["weather"]) > 0:
                            self.data[city]["description"] = response["weather"][0]["main"]  # This gets 'Clear'
                            self.data[city]["weather_id"] = response["weather"][0]["id"]
                        else:
                            self.data[city]["description"] = "Clear"
                            self.data[city]["weather_id"] = 800  # Default to Clear
                        self.data[city]["temp"] = response["main"]["temp"]
                        self.data[city]["feels_like"] = response["main"]["feels_like"]
                        self.data[city]["humidity"] = response["main"]["humidity"]
                        self.data[city]["wind"] = response["wind"]["speed"] # 10.36 mph
                        self.data[city]["sunrise"] = response["sys"]["sunrise"] # 1691673600 (Unix Timestamp)
                        self.data[city]["sunset"] = response["sys"]["sunset"] # 1691720400 (Unix Timestamp)
                        self.data[city]["timezone"] = response["timezone"] # 7200 (Seconds offset from UTC)
                        self.data[city]["current_time"] = response["dt"] # 1691720400 (Unix Timestamp)
                        icon_code = response['weather'][0]['icon']
                        
                        # 2. Fetch and Process Icon Image
                        icon_url = f"http://openweathermap.org/img/wn/{icon_code}@2x.png"
                        img_res = requests.get(icon_url, stream=True)
                        img = Image.open(io.BytesIO(img_res.content)).convert('RGBA')
                        
                        # NEAREST prevents the "blurry/orange" edges during resize
                        img = img.resize((32, 32), Image.NEAREST) 
                        
                        # Create a black background and paste the icon over it
                        # This "flattens" the transparency so the matrix doesn't get confused
                        clean_bg = Image.new("RGB", (32, 32), (0, 0, 0))
                        clean_bg.paste(img, (0, 0), img) 
                        self.icons[city] = clean_bg
                                
            except Exception as e:
                print(f"Weather Fetch Error: {e}")
                
            time.sleep(900) # 15 minute cooldown


    def render(self, canvas, font, small_font, y_offset=0):
        if not self.data:
            return
                
        if not self.is_transitioning:
            if (time.time() - self.last_switch_time) >= 6: # Switch every 6 seconds
                self.is_transitioning = True
                self.local_push = 0
                self.next_idx = (self.current_idx + 1) % len(self.cities)

        if self.is_transitioning:
            self.local_push += 4  # Slide speed (pixels per frame)
            if self.local_push >= 64:
                self.current_idx = self.next_idx
                self.is_transitioning = False
                self.local_push = 0
                self.last_switch_time = time.time()

        # 2. Frame Drawing Loop
        # Draw current city and next city if transitioning
        display_indices = [self.current_idx, self.next_idx] if self.is_transitioning else [self.current_idx]
        
        for i, idx in enumerate(display_indices):
            city_name = self.cities[idx]
            if city_name not in self.data: continue
            
            # Calculate vertical position for this city's frame
            y_base = 0 if i == 0 else 64
            # The Magic Formula adapted for 64px height:
            frame_y = y_offset + y_base - self.local_push

            # Data Extraction for current city in loop
            d = self.data[city_name]
            icon_img = self.icons.get(city_name)
            temp = int(d.get("temp", 0))
            hum = d.get("humidity", 0)
            wind = d.get("wind", 0)
            desc = d.get("description", "Clear")
            timezone_offset = d.get("timezone", 0)
            current_time = datetime.datetime.utcfromtimestamp(d.get("current_time", 0)+timezone_offset).strftime("%I:%M %p")

            # --- SECTION 1: HEADER ---
            graphics.DrawText(canvas, small_font, 2, frame_y + 8, self.city_color, city_name[:12])
            graphics.DrawText(canvas, small_font, 80, frame_y + 8, self.white, current_time)
            graphics.DrawLine(canvas, 0, frame_y + 10, 127, frame_y + 10, graphics.Color(50, 50, 50))

           # --- SECTION 2: MIDDLE LEFT (32x32 Icon centered in its zone) ---
            try:
                # We target a 32x32 area for the icon as per your diagram
                # Resize logic should be in update(), but we ensure drawing is contained here
                width, height = self.icons[city_name].size if icon_img else (0, 0)
                icon_x_start = -5
                icon_y_start = 5
                
                for y in range(height):
                    for x in range(width):
                        r, g, b = self.icons[city_name].getpixel((x, y))
                        if r > 30 or g > 30 or b > 30:
                            # Scale logic: if your img is 64x64, we divide by 2 to fit 32x32 zone
                            # Assuming you resize to 32x32 in update() for best results
                            canvas.SetPixel(x + icon_x_start, y + icon_y_start + frame_y + y_offset, r, g, b)
            except Exception as e:
                print(f"Icon render error: {e}")

            # --- SECTION 3: MIDDLE RIGHT (Temperature & Description) ---
            # Centered in the remaining space (x=64 to 127)
            graphics.DrawText(canvas, self.medium_font, 24, frame_y + y_offset + 22, self.white, f"{temp}F/{(temp - 32) * 5/9:.1f}C")
            graphics.DrawText(canvas, small_font, 24, frame_y + y_offset + 32, self.city_color, desc)

            # --- SECTION 4: FOOTER (y=44 to 63) ---
            # Divider Line
            graphics.DrawLine(canvas, 0, frame_y + y_offset + 46, 127, frame_y + y_offset + 46, graphics.Color(50, 50, 50))
            
            humidity = f"{hum}% {int(wind)}mph"
            graphics.DrawText(canvas, small_font, 80, frame_y + y_offset + 18, self.temp_color, humidity)
            sunrise_time = datetime.datetime.fromtimestamp(self.data[city_name].get("sunrise", 0)).strftime("%I:%M %p")
            # Convert sunset timestamp to city's timezone
            sunset_dt = datetime.datetime.utcfromtimestamp(self.data[city_name].get("sunset", 0) + timezone_offset)
            sunset_time = sunset_dt.strftime("%I:%M %p")
            graphics.DrawText(canvas, small_font, 80, frame_y + y_offset + 28, self.temp_color, f"{sunset_time}")
            # Convert sunset timestamp to city's timezone
            graphics.DrawText(canvas, small_font, 80, frame_y + y_offset + 28, self.temp_color, f"{sunset_time}")