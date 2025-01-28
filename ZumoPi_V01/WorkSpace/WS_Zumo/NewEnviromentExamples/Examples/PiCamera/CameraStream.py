#!/usr/bin/env python3

import io
import time
import logging
import socketserver
from http import server
from picamzero import Camera
from PIL import Image
import numpy as np

PAGE = """\
<html>
<head>
<title>Raspberry Pi - Camera (picamzero)</title>
</head>
<body>
<center><h1>Raspberry Pi - Camera (picamzero)</h1></center>
<center><img src="stream.mjpg" width="640" height="480"></center>
</body>
</html>
"""

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()

        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)

        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()

            try:
                while True:
                    # Capture the raw array at the default (likely high) resolution
                    raw_array = cam.capture_array()

                    # Convert to PIL
                    pil_img = Image.fromarray(raw_array)

                    # Resize down to 320×240 using a decent resampling filter
                    #pil_resized = pil_img.resize((320, 240), Image.LANCZOS)

                    # Convert resized image to JPEG bytes
                    frame_io = io.BytesIO()
                    pil_img.save(frame_io, format='JPEG')
                    frame_data = frame_io.getvalue()

                    # Write in MJPEG multipart format
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(frame_data)))
                    self.end_headers()
                    self.wfile.write(frame_data)
                    self.wfile.write(b'\r\n')

                    # Throttle to about 3 frames per second
                    time.sleep(0.2)

            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e)
                )

        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == '__main__':
    cam = Camera()
    # Example: Flip the camera horizontally if desired
    cam.flip_camera(hflip=True)
    cam.video_size = (320, 240)   # Lower resolution for real-time capture
    cam.still_size = (320, 240)   # Ensure still captures also match if you're doing snapshots
    
    address = ('', 8000)
    with StreamingServer(address, StreamingHandler) as server:
        print("Server started at http://0.0.0.0:8000")
        server.serve_forever()
