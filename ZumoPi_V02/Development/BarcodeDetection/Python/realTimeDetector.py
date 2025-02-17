import cv2
import time
from hub_detector import detect_hubs  # Make sure hub_detector.py is in the same directory

def main():
    # Open the default webcam.
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Set resolution to 1280x720.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    # Parameters (non-debug mode, adjust as needed).
    circle_diameter = 100
    expected_dark_fraction = 0.85
    min_blob_area = circle_diameter*2.5 # blob size = diameter*resolution/400 1080p = 2.5

    # Create a named window to display output.
    cv2.namedWindow("Real-Time Hub Detection", cv2.WINDOW_NORMAL)

    # Initialize the previous frame time for FPS calculation.
    prev_frame_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame from webcam. Exiting.")
            break

        # Calculate FPS.
        current_time = time.time()
        fps = 1.0 / (current_time - prev_frame_time)
        prev_frame_time = current_time

        # Convert frame from BGR to RGB.
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Call detect_hubs from the library.
        hubs = detect_hubs(frame_rgb, DEBUG=False, circle_diameter=circle_diameter,
                           expected_dark_fraction=expected_dark_fraction,
                           min_blob_area=min_blob_area)

        # Create a copy of the original frame for overlays.
        overlay = frame.copy()
        
        # Overlay detected hubs.
        for idx, hub in enumerate(hubs):
            c = hub['center']
            r = int(hub['radius'])
            c_int = (int(c[0]), int(c[1]))
            
            # Draw a green circle and a green "X" at the hub center.
            cv2.circle(overlay, c_int, r, (0, 255, 0), 2)
            cv2.line(overlay, (c_int[0] - 10, c_int[1] - 10),
                     (c_int[0] + 10, c_int[1] + 10), (0, 255, 0), 2)
            cv2.line(overlay, (c_int[0] - 10, c_int[1] + 10),
                     (c_int[0] + 10, c_int[1] - 10), (0, 255, 0), 2)
            
            # Annotate each of the 4 LED blobs.
            for j in range(1, 5):
                blob_field = f'blob{j}'
                blob = hub[blob_field]
                blob_center = blob['center']
                letter = blob['color'][0].upper()
                blob_center_int = (int(blob_center[0]), int(blob_center[1]))
                cv2.putText(overlay, letter, blob_center_int,
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2, cv2.LINE_AA)
            
            # Print hub data to the console.
            blob_colors = " ".join([hub[f'blob{i}']['color'] for i in range(1, 5)])
            print(f"Hub {idx+1}: Center=({c[0]:.1f}, {c[1]:.1f}), Radius={r:.1f}, "
                  f"DF={hub['darkFraction']:.2f}, Blobs: {blob_colors}")

        # Overlay the FPS on the image.
        cv2.putText(overlay, f"FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (255, 0, 0), 2, cv2.LINE_AA)

        # Display the overlay.
        cv2.imshow("Real-Time Hub Detection", overlay)

        # Exit on 'q' key press.
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Clean up.
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
