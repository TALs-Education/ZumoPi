import cv2
import numpy as np
import matplotlib.pyplot as plt

def detect_hubs(img, DEBUG=False, circle_diameter=100, 
                expected_dark_fraction=0.75, min_blob_area=100):
    """
    detect_hubs Detects circular hubs with LED markers on a blue background by using
    a grayscale mask (non-blue intensity) with HoughCircles.
    
    Parameters:
      img                   - Input RGB image as a NumPy array.
      DEBUG                 - If True, displays debug images and prints info.
      circle_diameter       - Nominal diameter for circle detection (default: 100).
      expected_dark_fraction- Expected average non-blue intensity (normalized 0-1)
                              inside a hub (default: 0.75).
      min_blob_area         - Minimum area in pixels for a blob (default: 100).
    
    Returns:
      hubs - A list of dictionaries. Each hub dict contains:
             'center': (x, y), 'radius': r, 'numBlobs': number of detected blobs,
             'darkFraction': computed average non-blue intensity,
             and for each blob, keys 'blob1', 'blob2', 'blob3', 'blob4' with:
                 'center' and 'color'.
    """
    # --- 1. Resize image if larger than 1920x1080 (1080p, 16:9) ---
    origH, origW = img.shape[:2]
    maxW, maxH = 1920, 1080
    if origW > maxW or origH > maxH:
        scale = min(maxW / origW, maxH / origH)
        new_w = int(origW * scale)
        new_h = int(origH * scale)
        img = cv2.resize(img, (new_w, new_h))
        if DEBUG:
            print(f"Resized image from ({origW}, {origH}) to ({new_w}, {new_h})")
    
    # Create a grayscale version for local blob segmentation.
    gray_img_original = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # --- 2. Create a grayscale mask based on the blue gradient ---
    R = img[:, :, 0].astype(np.float32)
    G = img[:, :, 1].astype(np.float32)
    B = img[:, :, 2].astype(np.float32)
    max_RG = np.maximum(R, G)
    blue_grad = B - max_RG
    blue_grad = np.where(blue_grad < 0, 0, blue_grad)
    norm_blue = np.empty_like(blue_grad)
    cv2.normalize(blue_grad, norm_blue, 0, 255, cv2.NORM_MINMAX)
    blue_mask = norm_blue.astype(np.uint8)
    non_blue_mask = 255 - blue_mask
    non_blue_norm = non_blue_mask.astype(np.float32)
    non_blue_norm /= 255.0
    
    if DEBUG:
        plt.figure()
        plt.imshow(non_blue_mask, cmap='gray')
        plt.title("Non-blue Grayscale Mask")
        plt.show()
    
    # --- 3. Use HoughCircles on the non-blue mask ---
    non_blue_blur = cv2.medianBlur(non_blue_mask, 5)
    
    min_radius = int(np.floor((circle_diameter * 0.75) / 2))
    max_radius = int(np.floor((circle_diameter * 1.25) / 2))
    
    circles = cv2.HoughCircles(non_blue_blur, cv2.HOUGH_GRADIENT, dp=1, 
                               minDist=circle_diameter,
                               param1=100, param2=30,
                               minRadius=min_radius, maxRadius=max_radius)
    
    # --- Debug Plot: Raw HoughCircles Detections ---
    hough_img = cv2.cvtColor(non_blue_blur, cv2.COLOR_GRAY2BGR)
    if circles is not None:
        circles = np.uint16(np.around(circles))
        for (c_x, c_y, r) in circles[0, :]:
            cv2.circle(hough_img, (c_x, c_y), r, (0, 255, 0), 2)
            cv2.circle(hough_img, (c_x, c_y), 2, (0, 0, 255), 3)
    if DEBUG:
        plt.figure()
        plt.imshow(hough_img)
        plt.title("Raw HoughCircles Detections on Non-blue Mask")
        plt.show()
    
    hubs = []
    failed_candidates = []
    lower_dark = expected_dark_fraction * 0.75
    upper_dark = expected_dark_fraction * 1.25
    
    # --- Precompute coordinate grid once ---
    rows, cols = non_blue_norm.shape
    y_grid, x_grid = np.ogrid[0:rows, 0:cols]
    
    # --- 4. Process each detected circle ---
    if circles is not None:
        for (c_x, c_y, r) in circles[0, :]:
            c_x, c_y, r = int(c_x), int(c_y), int(r)
            circle_mask = (x_grid - c_x)**2 + (y_grid - c_y)**2 <= r**2
            dark_fraction = np.mean(non_blue_norm[circle_mask])
            
            if lower_dark <= dark_fraction <= upper_dark:
                # --- 5. Analyze blobs inside the candidate hub on the original grayscale image ---
                local_gray = cv2.bitwise_and(gray_img_original, gray_img_original,
                                               mask=(circle_mask.astype(np.uint8) * 255))
                ret, local_bin = cv2.threshold(local_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # Find connected components.
                num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(local_bin, connectivity=8)
                valid_centroids = []
                valid_colors = []
                color_threshold = 30
                
                # Process each blob (label 0 is background).
                for label in range(1, num_labels):
                    area = stats[label, cv2.CC_STAT_AREA]
                    if DEBUG:
                        print(f"Blob {label}: Area = {area}")
                    if area >= min_blob_area:
                        ys, xs = np.where(labels == label)
                        mean_R = np.mean(R[ys, xs])
                        mean_G = np.mean(G[ys, xs])
                        mean_B = np.mean(B[ys, xs])
                        
                        if (abs(mean_R - mean_G) < color_threshold and 
                            abs(mean_R - mean_B) < color_threshold and 
                            abs(mean_G - mean_B) < color_threshold):
                            blob_color = "white"
                        elif mean_R > mean_G and mean_R > mean_B:
                            blob_color = "red"
                        elif mean_G > mean_R and mean_G > mean_B:
                            blob_color = "green"
                        elif mean_B > mean_R and mean_B > mean_G:
                            blob_color = "blue"
                        else:
                            blob_color = "unknown"
                        
                        valid_centroids.append(centroids[label])
                        valid_colors.append(blob_color)
                
                num_blobs = len(valid_centroids)
                if num_blobs == 4:
                    angles = []
                    for centroid in valid_centroids:
                        dx = centroid[0] - c_x
                        dy = centroid[1] - c_y
                        angle = np.mod(np.arctan2(dx, -dy), 2 * np.pi)
                        angles.append(angle)
                    sort_order = np.argsort(angles)
                    sorted_centroids = [valid_centroids[i] for i in sort_order]
                    sorted_colors = [valid_colors[i] for i in sort_order]
                    
                    hub = {
                        "center": (float(c_x), float(c_y)),
                        "radius": float(r),
                        "numBlobs": num_blobs,
                        "darkFraction": dark_fraction
                    }
                    for k in range(4):
                        hub[f"blob{k+1}"] = {
                            "center": (float(sorted_centroids[k][0]), float(sorted_centroids[k][1])),
                            "color": sorted_colors[k]
                        }
                    hubs.append(hub)
                    
                    if DEBUG:
                        print(f"Valid Hub: Center=({c_x}, {c_y}), Radius={r}, DarkFraction={dark_fraction:.2f}, 4 blobs detected")
                else:
                    reason = f"Blob count: {num_blobs}"
                    failed_candidates.append({"center": (c_x, c_y), "radius": r, "reason": reason})
                    if DEBUG:
                        print(f"Candidate hub at ({c_x}, {c_y}) with radius={r} failed: {num_blobs} blobs detected (DarkFraction={dark_fraction:.2f})")
            else:
                reason = f"Dark fraction: {dark_fraction:.2f}"
                failed_candidates.append({"center": (c_x, c_y), "radius": r, "reason": reason})
                if DEBUG:
                    print(f"Circle filtered out: Center=({c_x}, {c_y}), Radius={r}, DarkFraction={dark_fraction:.2f}")
    else:
        if DEBUG:
            print("No circles detected by HoughCircles")
    
    if DEBUG:
        final_debug_img = img.copy()
        for hub in hubs:
            cx, cy = int(hub["center"][0]), int(hub["center"][1])
            r = int(hub["radius"])
            cv2.circle(final_debug_img, (cx, cy), r, (0, 255, 0), 2)
        for candidate in failed_candidates:
            cx, cy = candidate["center"]
            r = candidate["radius"]
            cv2.circle(final_debug_img, (cx, cy), r, (0, 0, 255), 2)
            cv2.putText(final_debug_img, candidate["reason"], (cx-20, cy+15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
        plt.figure()
        plt.imshow(final_debug_img)
        plt.title("Final Detected Hubs (Green=Valid, Red=Failed)")
        plt.show()
    
    return hubs
