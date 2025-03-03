#!/usr/bin/env python3

import time
import io
import base64
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
from picamzero import Camera
from PIL import Image, ImageDraw, ImageFont

# We'll track time between frames to estimate FPS
last_time = time.time()

# Optional: load a TrueType font for on-image text.
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
except:
    font = ImageFont.load_default()

# Initialize the picamzero camera
cam = Camera()
cam.flip_camera(hflip=True, vflip=False)  # Flip if needed
# By default, picamzero may capture full resolution (e.g., 2592×1944)
# You can explicitly set resolution if desired, e.g.:
cam.video_size = (640, 480)
cam.still_size = (640, 480)

def capture_annotated_frame():
    """
    Capture a frame from picamzero, annotate it with FPS, 
    compress to JPEG (quality=50), and return a base64 data URI.
    """
    global last_time

    # Calculate FPS from time delta
    current_time = time.time()
    delta = current_time - last_time
    if delta <= 0:
        delta = 1e-6
    fps = 1.0 / delta
    last_time = current_time

    # Grab the raw camera data (NumPy array)
    frame_array = cam.capture_array()

    # Convert to PIL Image
    pil_img = Image.fromarray(frame_array)

    # (Optional) Resize to reduce bandwidth, e.g. 640×480:
    # pil_img = pil_img.resize((640, 480), Image.LANCZOS)

    # Draw FPS text on the image
    draw = ImageDraw.Draw(pil_img)
    fps_text = f"FPS: {fps:.1f}"
    draw.text((10, 10), fps_text, fill="white", font=font)

    # Convert to JPEG with quality=50
    buffer = io.BytesIO()
    pil_img.save(buffer, format="JPEG", quality=50)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

    # Return data URI
    return "data:image/jpeg;base64," + encoded

# Build a minimal Dash application
app = dash.Dash(__name__)
app.layout = html.Div([
    html.H1("Camera Stream (picamzero + Dash)"),
    html.Img(id="live-image"),
    # Interval for ~1 FPS => 1000 ms
    dcc.Interval(id="interval-component", interval=1000, n_intervals=0)
])

@app.callback(
    Output("live-image", "src"),
    [Input("interval-component", "n_intervals")]
)
def update_image(n):
    """Callback that captures/encodes an image every ~100ms."""
    return capture_annotated_frame()

if __name__ == "__main__":
    # Run on port 8000, available on all interfaces
    app.run_server(host="0.0.0.0", port=8000, debug=False)
