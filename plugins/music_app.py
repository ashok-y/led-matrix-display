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
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.spotify_cfg = self.config.get("music", {})
        
        self.auth_manager = SpotifyOAuth(
            client_id=self.spotify_cfg.get("spotify_client_id"),
            client_secret=self.spotify_cfg.get("spotify_client_secret"),
            redirect_uri=self.spotify_cfg.get("spotify_redirect_uri"),
            cache_path="/home/pi/workspace/led_matrix/.spotify_cache",
            open_browser=False  
        )
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
        
        self.current_track = None
        self.album_img = None
        self.last_track_id = None

    def get_color(self, r, g, b):
        """Helper to scale any RGB color by the global brightness config (0-255)."""
        brightness = int(self.config.get("brightness", 125))
        # Scale 0-255 based on the brightness ratio
        scale = brightness / 255.0
        return graphics.Color(int(r * scale), int(g * scale), int(b * scale))

    def update(self):
        while True:
            try:
                track = self.sp.currently_playing()
                if track and track.get('item'):
                    item = track['item']
                    track_id = item['id']
                    
                    self.current_track = {
                        "name": item['name'],
                        "artist": item['artists'][0]['name'],
                        "progress": track['progress_ms'],
                        "duration": item['duration_ms'],
                        "is_playing": track['is_playing']
                    }

                    if track_id != self.last_track_id:
                        album_url = item['album']['images'][0]['url']
                        res = requests.get(album_url)
                        img = Image.open(io.BytesIO(res.content)).convert('RGB')
                        self.album_img = img.resize((32, 32), Image.NEAREST)
                        self.last_track_id = track_id
                else:
                    self.current_track = None
            except Exception as e:
                print(f"Spotify Update Error: {e}")
            time.sleep(1)

    def draw_spotify_logo(self, canvas, x, y):
        # Using scaled Spotify Green
        green = self.get_color(29, 185, 84)
        black = graphics.Color(0, 0, 0) # Black is always black
        
        graphics.DrawLine(canvas, x+2, y, x+6, y, green)
        graphics.DrawLine(canvas, x+1, y+1, x+7, y+1, green)
        for i in range(2, 7):
            graphics.DrawLine(canvas, x, y+i, x+8, y+i, green)
        graphics.DrawLine(canvas, x+1, y+7, x+7, y+7, green)
        graphics.DrawLine(canvas, x+2, y+8, x+6, y+8, green)

        graphics.DrawLine(canvas, x+2, y+2, x+6, y+2, black)
        graphics.DrawLine(canvas, x+1, y+4, x+7, y+4, black)
        graphics.DrawLine(canvas, x+2, y+6, x+6, y+6, black)
    
    def format_time(self, ms):
        seconds = int((ms / 1000) % 60)
        minutes = int((ms / (1000 * 60)) % 60)
        return f"{minutes}:{seconds:02d}"

    def render(self, canvas, font, small_font, y_offset=0):
        # 1. Define Dynamic Colors based on Brightness
        white = self.get_color(255, 255, 255)
        green = self.get_color(30, 215, 96)
        gray = self.get_color(100, 100, 100)
        dark_gray = self.get_color(40, 40, 40)

        if not self.current_track:
            graphics.DrawText(canvas, small_font, 40, y_offset + 16, white, "Spotify Idle")
            return

        # 2. Draw Album Art (Left 32x32)
        if self.album_img:
            # Note: We apply brightness to the pixels manually here
            brightness_scale = int(self.config.get("brightness", 125)) / 255.0
            for y in range(32):
                for x in range(32):
                    r, g, b = self.album_img.getpixel((x, y))
                    canvas.SetPixel(x, y + y_offset, int(r * brightness_scale), int(g * brightness_scale), int(b * brightness_scale))

        # 3. Text Scrolling Config
        win_left = 36    # Start after album art + gap
        win_right = 110  # Leave room for Spotify Logo
        win_width = win_right - win_left
        
        # Calculate track name width
        text_width = sum([small_font.CharacterWidth(ord(c)) for c in self.current_track['name']])

        # 4. Draw Track Name & Artist (with mask logic)
        if text_width > win_width:
            offset = int(time.time() * 25) % (text_width + 20)
            x_pos = win_left - offset
        else:
            x_pos = win_left

        # Render Text
        graphics.DrawText(canvas, small_font, x_pos, y_offset + 10, white, self.current_track['name'])
        graphics.DrawText(canvas, small_font, win_left, y_offset + 18, green, self.current_track['artist'])

        # 5. Masking (Cleans up scrolling text over album art and logo)
        # Vertical slice for album art is 0-32, we mask just the text area
        for y in range(y_offset, y_offset + 12): # Only mask the track name line
            for x in range(0, win_left): # Left Mask
                if x < 32: continue # Don't erase the album art itself
                canvas.SetPixel(x, y, 0, 0, 0)
            for x in range(win_right, 128): # Right Mask
                canvas.SetPixel(x, y, 0, 0, 0)

        # 6. Spotify Logo
        self.draw_spotify_logo(canvas, 116, y_offset + 2)

        # 7. Progress Bar
        bar_x = 36
        bar_y = 22
        bar_w = 80
        progress_pct = self.current_track['progress'] / self.current_track['duration']
        filled_w = int(bar_w * progress_pct)

        # Background of bar
        graphics.DrawLine(canvas, bar_x, y_offset + bar_y, bar_x + bar_w, y_offset + bar_y, dark_gray)
        # Filled part of bar
        if filled_w > 0:
            graphics.DrawLine(canvas, bar_x, y_offset + bar_y, bar_x + filled_w, y_offset + bar_y, green)

        # 8. Timestamps
        graphics.DrawText(canvas, small_font, bar_x, y_offset + 30, gray, self.format_time(self.current_track['progress']))
        graphics.DrawText(canvas, small_font, bar_x + 55, y_offset + 30, gray, self.format_time(self.current_track['duration']))