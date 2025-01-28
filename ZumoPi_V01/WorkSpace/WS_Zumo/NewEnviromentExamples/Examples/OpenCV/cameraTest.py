import cv2
from picamzero import Camera

def main():
    cam = Camera()
    
    # If your picamzero version allows these attributes, adjust as needed:
    cam.video_size = (640, 480)   # Lower resolution for real-time capture
    cam.still_size = (640, 480)   # Ensure still captures also match if you're doing snapshots
    # Optionally:
    # cam.framerate = 30

    while True:
        frame_rgb = cam.capture_array()  # Should now be 640x480 natively
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        
        cv2.imshow("Camera Feed (640x480)", frame_bgr)

        # Quit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
