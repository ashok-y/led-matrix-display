import time
import requests
import io
import json
from PIL import Image
from rgbmatrix import graphics
from base_app import MatrixApp
import spotipy
from spotipy.oauth2 import SpotifyOAuth

class MusicApp(MatrixApp):
    def __init__(self):
        super().__init__()
        # Load Spotify credentials from config
        self.config = json.load(open("./config/config.json"))
        self.spotify_cfg = self.config.get("music", {})
        
        # Initialize Auth Manager with your existing cache
        self.auth_manager = SpotifyOAuth(
            client_id=self.spotify_cfg.get("spotify_client_id"),
            client_secret=self.spotify_cfg.get("spotify_client_secret"),
            redirect_uri=self.spotify_cfg.get("spotify_redirect_uri"),
            cache_path="/home/pi/workspace/led_matrix/.spotify_cache", # Ensure your JSON token is saved here
            open_browser=False  
        )
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
        
        self.current_track = None
        self.album_img = None
        self.last_track_id = None
        self.brightness = self.spotify_cfg.get("brightness", 125)
        self.white = graphics.Color(self.brightness, self.brightness, self.brightness)
        self.bg_color = graphics.Color(40, 40, 40)    # Dark Grey
        self.bar_color = graphics.Color(29, 185, 84) # Spotify Green

    def update(self):
        """Fetch Spotify data every 5 seconds"""
        while True:
            try:
                track = self.sp.currently_playing()
                if track and track.get('item'):
                    item = track['item']
                    track_id = item['id']
                    
                    # Update data dictionary
                    self.current_track = {
                        "name": item['name'],
                        "artist": item['artists'][0]['name'],
                        "progress": track['progress_ms'],
                        "duration": item['duration_ms'],
                        "is_playing": track['is_playing']
                    }

                    # Only download and process album art if the song changed
                    if track_id != self.last_track_id:
                        album_url = item['album']['images'][0]['url']
                        res = requests.get(album_url)
                        img = Image.open(io.BytesIO(res.content)).convert('RGB')
                        # Resize to 64x64 for the left side of your 128x64 screen
                        self.album_img = img.resize((32, 32), Image.NEAREST)
                        self.last_track_id = track_id
                else:
                    self.current_track = None
            except Exception as e:
                print(f"Spotify Update Error: {e}")
            
            time.sleep(1)
    def draw_spotify_logo(self, canvas, x, y):
        """Draws a small 9x9 Spotify icon"""
        green = graphics.Color(29, 185, 84)
        # Circular-ish background
        graphics.DrawLine(canvas, x+2, y, x+6, y, green)
        graphics.DrawLine(canvas, x+1, y+1, x+7, y+1, green)
        for i in range(2, 7):
            graphics.DrawLine(canvas, x, y+i, x+8, y+i, green)
        graphics.DrawLine(canvas, x+1, y+7, x+7, y+7, green)
        graphics.DrawLine(canvas, x+2, y+8, x+6, y+8, green)

        # Black "Waves" (The 3 stripes)
        black = graphics.Color(0, 0, 0)
        graphics.DrawLine(canvas, x+2, y+2, x+6, y+2, black)
        graphics.DrawLine(canvas, x+1, y+4, x+7, y+4, black)
        graphics.DrawLine(canvas, x+2, y+6, x+6, y+6, black)
    
    def format_time(self, ms):
        """Helper to convert ms to M:SS"""
        seconds = int((ms / 1000) % 60)
        minutes = int((ms / (1000 * 60)) % 60)
        return f"{minutes}:{seconds:02d}"

    def render(self, canvas, font, small_font, y_offset=0):
        if not self.current_track:
            graphics.DrawText(canvas, small_font, 30, y_offset + 32, self.white, "Spotify Idle")
            return

        # 1. Draw Album Art (Left Side - looks like you're using 32x32 now)

        # 2. Setup Colors and Positions
        text_x = 0
        white = graphics.Color(self.brightness, self.brightness, self.brightness)
        green = graphics.Color(30, 215, 96) 
        gray = graphics.Color(100, 100, 100) # Dimmer color for timestamps
        text_width = sum([font.CharacterWidth(ord(c)) for c in self.current_track['name']]) 

        win_left = 34    # Starts after album art
        win_right = 100   # Your custom right-side limit
        win_width = win_right - win_left
        # 3. Handle Scrolling
        # We use time to move the text. 
        # Adjust '20' to change speed (higher = slower)
        if text_width > win_width:
            # Calculate an offset that loops
            # It moves from 0 to (text_width + gap)
            speed = 30
            scroll_range = text_width + 15 # Total distance to scroll before looping
            total_dist = text_width + 20 # 20px gap
            offset = int(time.time() * speed) % scroll_range
            
            # Calculate x: start at the right of the window and move left
            x_pos = win_right - offset
        else:
            # Center it or keep it at 0 if it fits
            x_pos = win_left
            # Track Name & Artist
        graphics.DrawText(canvas, small_font, text_x + x_pos, y_offset + 10, white, self.current_track['name'])
        graphics.DrawText(canvas, small_font, text_x + x_pos, y_offset + 17, green, self.current_track['artist'])
        # 4. THE DUAL MASK (Cleaning the edges)
        # This erases anything outside your 34-60 window
        for y in range(y_offset, y_offset + 28):
            # Mask Left (over album art area)
            for x in range(0, win_left):
                canvas.SetPixel(x, y, 0, 0, 0)
            
            # Mask Right (anything past your limit)
            for x in range(win_right + 1, canvas.width):
                canvas.SetPixel(x, y, 0, 0, 0)

        if self.album_img:
            for y in range(32):
                for x in range(32):
                    r, g, b = self.album_img.getpixel((x, y))
                    canvas.SetPixel(x, y + y_offset, r, g, b)
                
        # Spotify Logo / Status
        self.draw_spotify_logo(canvas, 116, y_offset + 2)

        # 3. Progress Bar Math
        bar_x_start = 34
        bar_y_pos = 20 
        bar_width = 55
        bar_thickness = 4
        
        progress_ms = self.current_track['progress']
        duration_ms = self.current_track['duration']
        progress_pct = progress_ms / duration_ms
        filled_width = int(bar_width * progress_pct)

        # Draw Thick Bar
        for i in range(bar_thickness):
            current_y = y_offset + bar_y_pos + i
            graphics.DrawLine(canvas, bar_x_start, current_y, bar_x_start + bar_width, current_y, self.bg_color)
            if filled_width > 0:
                graphics.DrawLine(canvas, bar_x_start, current_y, bar_x_start + filled_width, current_y, self.bar_color)

        # 4. Timestamps (Positioned right under the bar)
        current_ts = self.format_time(progress_ms)
        total_ts = self.format_time(duration_ms)

        # Current Time (Left aligned with bar)
        graphics.DrawText(canvas, small_font, bar_x_start, y_offset + 31, gray, current_ts)
        
        # Total Time (Right aligned with end of bar)
        # Offset by ~20 pixels from the right to account for text width
        graphics.DrawText(canvas, small_font, bar_x_start + 35, y_offset + 31, gray, total_ts)