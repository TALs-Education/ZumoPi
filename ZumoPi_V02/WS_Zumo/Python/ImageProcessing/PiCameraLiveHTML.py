import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import base64
import time
import cv2
from picamera2 import Picamera2

# Initialize the camera
picam2 = Picamera2()
preview_config = picam2.create_preview_configuration(
    {"format": "RGB888", "size": (640, 480)}
)
picam2.configure(preview_config)
picam2.start()

# Global variables to track FPS
last_time = time.time()
frame_count = 0
current_fps = 0.0

app = dash.Dash(__name__)
app.layout = html.Div([
    html.Img(id='live-image'),
    html.Div(id='fps-display', style={'fontSize': '20px', 'marginTop': '10px'}),
    # Interval in milliseconds (200 ms -> up to ~5 updates/sec if system can keep up)
    dcc.Interval(id='interval-component', interval=100, n_intervals=0)
])

@app.callback(
    [Output('live-image', 'src'),
     Output('fps-display', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_image(n_intervals):
    global last_time, frame_count, current_fps
    
    # Measure FPS based on callback firing rate
    frame_count += 1
    elapsed = time.time() - last_time
    if elapsed >= 1.0:
        current_fps = frame_count / elapsed
        frame_count = 0
        last_time = time.time()
    
    # Capture the latest image from the camera
    frame = picam2.capture_array()
    
    # Compress the frame as JPEG (quality = 50)
    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
    # Convert to Base64 for embedding in HTML
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    data_uri = f"data:image/jpeg;base64,{jpg_as_text}"
    
    # Return the image and current FPS display
    return data_uri, f"FPS: {current_fps:.2f}"

if __name__ == '__main__':
    # Set host='0.0.0.0' to make the app accessible on your local network
    app.run_server(port=8500, host='0.0.0.0', debug=False, use_reloader=False)