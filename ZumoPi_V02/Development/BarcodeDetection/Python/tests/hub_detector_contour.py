import cv2
import numpy as np
import matplotlib.pyplot as plt

def detect_hubs(img, DEBUG=False, circle_diameter=100, 
                expected_dark_fraction=0.75, min_blob_area=100):
    """
    detect_hubs Detects circular hubs with LED markers on a blue background using
    a black mask to find candidate regions via contour detection.
    
    It filters candidates by ensuring:
      - The contour’s arc length is within ±25% of the expected circumference (π*circle_diameter).
      - The contour’s area is within ±25% of the expected ideal area (π*(circle_diameter/2)^2).
      - The candidate’s dark fraction is within the expected range.
      
    Then, for each candidate hub, a local region is extracted from the original grayscale
    image and Otsu thresholding is applied to detect LED blobs.
    
    Parameters:
      img                   - Input RGB image as a NumPy array.
      DEBUG                 - If True, displays debug images and prints diagnostic info.
      circle_diameter       - Nominal diameter for circle detection.
      expected_dark_fraction- Expected fraction (normalized 0-1) of black pixels inside a hub.
      min_blob_area         - Minimum area (in pixels) for a valid blob.
    
    Returns:
      hubs - A list of dictionaries with detected hub info, including:
             'center', 'radius', 'numBlobs', 'darkFraction',
             'contourLength', 'circularity', and for each blob (blob1..blob4): 'center' and 'color'.
      Also, failed candidate information is stored in 'failed_candidates'.
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
     
    # --- 2. Create a Black Mask using HSV ---
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    lower_black = np.array([0, 0, 0])
    upper_black = np.array([180, 255, 70])
    black_mask = cv2.inRange(hsv, lower_black, upper_black)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    if DEBUG:
        plt.figure()
        plt.imshow(black_mask, cmap='gray')
        plt.title("Black Mask")
        plt.show()
    
    # --- 3. Find Contours on the Black Mask ---
    contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours_debug = img.copy()
    cv2.drawContours(contours_debug, contours, -1, (255, 0, 0), 2)
    if DEBUG:
        plt.figure()
        plt.imshow(cv2.cvtColor(contours_debug, cv2.COLOR_RGB2BGR))
        plt.title("Contours on Black Mask")
        plt.show()
    
    hubs = []
    failed_candidates = []
    
    # Precompute coordinate grid for the image.
    rows, cols = black_mask.shape
    y_grid, x_grid = np.ogrid[0:rows, 0:cols]
    
    # Define expected candidate parameters based on circle_diameter.
    expected_length = np.pi * circle_diameter  # Expected circumference
    expected_area = np.pi * (circle_diameter / 2)**2  # Expected ideal area
    
    min_radius = int((circle_diameter * 0.75)/2)
    max_radius = int((circle_diameter * 1.25)/2)
    
    # --- 4. Process each contour as a candidate hub ---
    for cnt in contours:
        (c_x, c_y), r = cv2.minEnclosingCircle(cnt)
        c_x, c_y, r = int(c_x), int(c_y), int(r)
        if r < min_radius or r > max_radius:
            continue
        
        # Check contour length against expected_length (±25%).
        contour_length = cv2.arcLength(cnt, True)
        if not (0.75 * expected_length <= contour_length <= 1.25 * expected_length):
            reason = f"Contour length {contour_length:.1f} not in [ {0.75*expected_length:.1f}, {1.25*expected_length:.1f} ]"
            failed_candidates.append({
                "center": (c_x, c_y),
                "radius": r,
                "reason": reason,
                "contourLength": contour_length
            })
            if DEBUG:
                print(f"Rejected circle at ({c_x},{c_y}): {reason}")
            continue
        
        # Check contour area against expected_area (±25%).
        contour_area = cv2.contourArea(cnt)
        if not (0.75 * expected_area <= contour_area <= 1.25 * expected_area):
            reason = f"Contour area {contour_area:.1f} not in [ {0.75*expected_area:.1f}, {1.25*expected_area:.1f} ]"
            failed_candidates.append({
                "center": (c_x, c_y),
                "radius": r,
                "reason": reason,
                "contourArea": contour_area
            })
            if DEBUG:
                print(f"Rejected circle at ({c_x},{c_y}): {reason}")
            continue
        
        # Calculate circularity.
        circle_area = np.pi * (r ** 2)
        if circle_area <= 0:
            continue
        circularity = contour_area / circle_area
        if circularity < 0.75:
            reason = f"Low circularity: {circularity:.2f}"
            failed_candidates.append({
                "center": (c_x, c_y),
                "radius": r,
                "reason": reason,
                "contourLength": contour_length,
                "circularity": circularity
            })
            if DEBUG:
                print(f"Rejected circle at ({c_x},{c_y}): {reason}")
            continue
        
        # Compute dark fraction using black_mask.
        circle_mask = (x_grid - c_x)**2 + (y_grid - c_y)**2 <= r**2
        binary_mask = (black_mask > 0).astype(np.float32)
        dark_fraction = np.mean(binary_mask[circle_mask])
        
        lower_dark = expected_dark_fraction * 0.75
        upper_dark = expected_dark_fraction * 1.25
        if not (lower_dark <= dark_fraction <= upper_dark):
            reason = f"Dark fraction {dark_fraction:.2f} not in [{lower_dark:.2f}, {upper_dark:.2f}]"
            failed_candidates.append({
                "center": (c_x, c_y),
                "radius": r,
                "reason": reason,
                "contourLength": contour_length,
                "circularity": circularity
            })
            if DEBUG:
                print(f"Rejected circle at ({c_x},{c_y}): {reason}")
            continue
        
        # --- 5. Blob Detection: Use local black_mask
        circle_mask_uint8 = (circle_mask.astype(np.uint8)) * 255
        local_bin = cv2.bitwise_and(black_mask, black_mask, mask=circle_mask_uint8)
        
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(local_bin, connectivity=8)
        valid_centroids = []
        valid_colors = []
        color_threshold = 30
        
        if DEBUG:
            plt.figure()
            plt.imshow(local_bin, cmap='gray')
            plt.title("Local Binary Image (Grayscale + Otsu)")
            plt.show()
        
        for label in range(1, num_labels):  # label 0 is background
            area = stats[label, cv2.CC_STAT_AREA]
            if DEBUG:
                print(f"Blob {label} at ({c_x},{c_y}): Area = {area}")
            if area >= min_blob_area:
                ys, xs = np.where(labels == label)
                mean_R = np.mean(img[ys, xs, 0])
                mean_G = np.mean(img[ys, xs, 1])
                mean_B = np.mean(img[ys, xs, 2])
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
            for ctd in valid_centroids:
                dx = ctd[0] - c_x
                dy = ctd[1] - c_y
                angle = np.mod(np.arctan2(dx, -dy), 2 * np.pi)
                angles.append(angle)
            sort_order = np.argsort(angles)
            sorted_ctd = [valid_centroids[i] for i in sort_order]
            sorted_col = [valid_colors[i] for i in sort_order]
            
            hub = {
                "center": (float(c_x), float(c_y)),
                "radius": float(r),
                "numBlobs": 4,
                "darkFraction": dark_fraction,
                "contourLength": contour_length,
                "circularity": circularity
            }
            for k in range(4):
                hub[f"blob{k+1}"] = {
                    "center": (float(sorted_ctd[k][0]), float(sorted_ctd[k][1])),
                    "color": sorted_col[k]
                }
            hubs.append(hub)
            if DEBUG:
                print(f"Valid hub at ({c_x},{c_y}), r={r}, darkFraction={dark_fraction:.2f}, "
                      f"Len={contour_length:.1f}, circ={circularity:.2f}, 4 blobs detected.")
        else:
            reason = f"Blob count: {num_blobs}"
            failed_candidates.append({
                "center": (c_x, c_y),
                "radius": r,
                "reason": reason,
                "contourLength": contour_length,
                "circularity": circularity
            })
            if DEBUG:
                print(f"Candidate hub at ({c_x},{c_y}) failed: {num_blobs} blobs detected (darkFraction={dark_fraction:.2f}).")
    
    if DEBUG:
        final_debug_img = img.copy()
        for hub in hubs:
            cx, cy = int(hub["center"][0]), int(hub["center"][1])
            r = int(hub["radius"])
            cv2.circle(final_debug_img, (cx, cy), r, (0, 255, 0), 2)
            for i in range(1, 5):
                blob = hub[f"blob{i}"]
                bx, by = int(blob["center"][0]), int(blob["center"][1])
                cv2.circle(final_debug_img, (bx, by), 4, (0, 255, 255), -1)
                cv2.putText(final_debug_img, blob["color"][0].upper(), (bx-10, by-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1, cv2.LINE_AA)
        for candidate in failed_candidates:
            cx, cy = candidate["center"]
            r = candidate["radius"]
            cv2.circle(final_debug_img, (cx, cy), r, (0, 0, 255), 2)
            cv2.putText(final_debug_img, candidate["reason"], (cx-20, cy+15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
            extra_txt = f"L:{candidate.get('contourLength',0):.1f}, C:{candidate.get('circularity',0):.2f}"
            cv2.putText(final_debug_img, extra_txt, (cx-20, cy+30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
        plt.figure()
        plt.imshow(final_debug_img)
        plt.title("Final Detected Hubs (Green=Valid, Red=Failed)")
        plt.show()
    
    return hubs