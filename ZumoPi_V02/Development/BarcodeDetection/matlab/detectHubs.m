function hubs = detectHubs(img, DEBUG, thresholdLevel, circleDiameter, expectedDarkFraction, minBlobArea)
% detectHubs Detects circular hubs with LED markers in an image.
%
%   hubs = detectHubs(img, DEBUG, thresholdLevel, circleDiameter, expectedDarkFraction, minBlobArea)
%
%   Processes the input RGB image to identify candidate circular hubs and
%   validates those having exactly 4 LED markers (blobs). In addition to a
%   simple grayscale threshold (for darkFraction), this function uses a
%   "blue gradient" mask to find black-on-blue circular hubs.
%
%   Input arguments:
%     img                  - Input RGB image.
%     DEBUG                - Boolean flag to display debug plots and print debug info (default: false).
%     thresholdLevel       - Grayscale threshold for binarization (default: 0.30).
%     circleDiameter       - Approx diameter for hub detection (default: 100). Allowed ±25%.
%     expectedDarkFraction - Expected fraction of dark area within each hub (default: 0.75). Allowed ±25%.
%     minBlobArea          - Minimum area (in pixels) to treat a connected component as a valid blob (default: 100).
%
%   Output:
%     hubs - Structure array with fields:
%            .center, .radius, .numBlobs, .darkFraction,
%            plus .blob1..blob4 (each with .center, .color).
%
%   Example:
%     img = imread('Image3.jpg');
%     hubs = detectHubs(img, true, 0.30, 100, 0.75, 200);

    % --------------------------- DEFAULTS ---------------------------
    if nargin < 6, minBlobArea = 50; end
    if nargin < 5, expectedDarkFraction = 0.85; end
    if nargin < 4, circleDiameter = 100; end
    if nargin < 3, thresholdLevel = 0.4; end
    if nargin < 2, DEBUG = false; end

    % ---------------------- 1. RESIZE IF LARGE ----------------------
    [origH, origW, ~] = size(img);
    maxW = 1280; 
    maxH = 720;
    if (origW > maxW || origH > maxH)
        scale = min(maxW/origW, maxH/origH);
        img = imresize(img, scale);
        if DEBUG
            fprintf('Image resized from (%d, %d) to (%d, %d)\n', ...
                origH, origW, size(img,1), size(img,2));
        end
    end

    % -------------- 2. CREATE INVERTED BINARY (FOR DARK FRACTION) --------------
    % We still use a simple grayscale threshold to measure "darkFraction" 
    % and later to detect internal blobs as black=0 (in the binImg).
    grayImg = rgb2gray(img);
    binImg = imbinarize(grayImg, thresholdLevel);
    binImg = ~binImg;  % invert => originally dark => white=1

    % ------------- 3. BUILD A "NON-BLUE" MASK (FOR CIRCLE DETECTION) -------------
    % Convert to double for arithmetic
    R = double(img(:,:,1));
    G = double(img(:,:,2));
    B = double(img(:,:,3));

    % "Blue gradient" = B - max(R,G). Clip negatives to zero.
    maxRG = max(R, G);
    blueGrad = B - maxRG;
    blueGrad(blueGrad < 0) = 0;

    % Normalize to [0..1], then scale to uint8 => [0..255]
    normBlue  = mat2gray(blueGrad);
    blueMask  = im2uint8(normBlue);

    % Invert => black objects on blue become "bright"
    nonBlueMask = 255 - blueMask;

    % (Optional) Reduce noise with median filter
    nonBlueMaskBlur = medfilt2(nonBlueMask, [5 5]);

    if DEBUG
        figure;
        imshow(nonBlueMaskBlur);
        title('Non-Blue Mask (Median-Filtered)');
    end

    % --------- 4. DETECT CIRCLES IN NON-BLUE MASK VIA IMFINDCIRCLES ---------
    % Convert circleDiameter => radius range ±25%
    minRadius = floor((circleDiameter * 0.75) / 2);
    maxRadius = floor((circleDiameter * 1.25) / 2);

    [centers, radii] = imfindcircles(nonBlueMaskBlur, [minRadius, maxRadius], ...
                                     'ObjectPolarity', 'bright', ...
                                     'Sensitivity',     0.80);

    % Debug plot of circle detection
    if DEBUG
        figure; 
        imshow(img);
        hold on;
        title('Candidate Circles (Black-on-Blue)');
        if ~isempty(centers)
            viscircles(centers, radii, 'Color', 'g');
        end
    end

    % ----------- 5. PREP FOR VALID HUB STORAGE -----------
    hubs = struct('center',{}, 'radius',{}, 'numBlobs',{}, 'darkFraction',{}, ...
                  'blob1',{}, 'blob2',{}, 'blob3',{}, 'blob4',{});
    validHubCount = 0;

    % Allowed range for darkFraction (±25% around expectedDarkFraction)
    darkFracMin = expectedDarkFraction * 0.75;
    darkFracMax = expectedDarkFraction * 1.25;

    % ----------- 6. EXAMINE EACH CIRCLE (CANDIDATE HUB) -----------
    for i = 1:length(radii)
        c = centers(i, :);  % (x, y)
        r = radii(i);

        % Create a logical mask for pixels inside this circle
        [X, Y] = meshgrid(1:size(binImg,2), 1:size(binImg,1));
        circleMask = ((X - c(1)).^2 + (Y - c(2)).^2) <= r^2;

        % darkFraction = fraction of circle area that is white=1 in binImg 
        % (white=1 in binImg => originally "dark" in the grayscale image).
        whiteCount  = sum(binImg(circleMask), 'all');
        circleArea  = sum(circleMask(:));
        darkFraction = whiteCount / circleArea;

        % Check if darkFraction is within acceptable range
        if (darkFraction >= darkFracMin && darkFraction <= darkFracMax)
            % ---------------- 6a. DETECT BLOBS INSIDE THE HUB ----------------
            % Restrict analysis to the circle region => set outside to white=1
            hubSubImage = binImg;
            hubSubImage(~circleMask) = 1;

            % Inside the circle, LED markers are black=0
            blackRegion = (hubSubImage == 0);

            % (Optional) Morphological opening to remove small noise
            se = strel('disk', 2);
            blackRegionSmooth = imopen(blackRegion, se);

            CC = bwconncomp(blackRegionSmooth, 8);
            stats = regionprops(CC, 'Centroid', 'Area');

            validCentroids = [];
            validColors    = {};
            colorThreshold = 30;  % difference threshold to classify 'white'

            for j = 1:length(stats)
                if stats(j).Area >= minBlobArea
                    validCentroids = [validCentroids; stats(j).Centroid]; %#ok<AGROW>
                    blobIndices    = CC.PixelIdxList{j};

                    % Compute mean color for each blob from the original image
                    meanR = mean(R(blobIndices));
                    meanG = mean(G(blobIndices));
                    meanB = mean(B(blobIndices));

                    % Classify blob color
                    if abs(meanR - meanG) < colorThreshold && ...
                       abs(meanR - meanB) < colorThreshold && ...
                       abs(meanG - meanB) < colorThreshold
                        blobColor = 'white';
                    elseif (meanR > meanG && meanR > meanB)
                        blobColor = 'red';
                    elseif (meanG > meanR && meanG > meanB)
                        blobColor = 'green';
                    elseif (meanB > meanR && meanB > meanG)
                        blobColor = 'blue';
                    else
                        blobColor = 'unknown';
                    end

                    validColors{end+1} = blobColor; %#ok<AGROW>
                end
            end

            numBlobs = size(validCentroids, 1);

            % ---------------- 6b. CHECK FOR EXACTLY 4 BLOBS ----------------
            if numBlobs == 4
                % Sort the 4 blobs in clockwise order, "up"=0 degrees
                angles = zeros(numBlobs, 1);
                for k = 1:numBlobs
                    dX = validCentroids(k,1) - c(1);
                    dY = validCentroids(k,2) - c(2);
                    % Use atan2(dX, -dY) so 0° = up (negative y)
                    angles(k) = mod(atan2(dX, -dY), 2*pi);
                end
                [~, sortOrder] = sort(angles);
                sortedCentroids = validCentroids(sortOrder, :);
                sortedColors    = validColors(sortOrder);

                % Store results in hubs structure
                validHubCount = validHubCount + 1;
                hubs(validHubCount).center       = c;
                hubs(validHubCount).radius       = r;
                hubs(validHubCount).numBlobs     = numBlobs;
                hubs(validHubCount).darkFraction = darkFraction;
                for k = 1:numBlobs
                    fieldName = sprintf('blob%d', k);
                    hubs(validHubCount).(fieldName).center = sortedCentroids(k, :);
                    hubs(validHubCount).(fieldName).color  = sortedColors{k};
                end

                % Debug: draw a green circle + mark the 4 blobs
                if DEBUG
                    viscircles(c, r, 'Color', 'g');
                    plot(c(1), c(2), 'gx', 'MarkerSize', 12, 'LineWidth', 2);
                    for k = 1:numBlobs
                        blobLetter = upper(sortedColors{k}(1));  
                        blobPos = sortedCentroids(k, :);
                        text(blobPos(1), blobPos(2), blobLetter, 'Color','k',...
                            'FontSize',14, 'FontWeight','bold', 'HorizontalAlignment','center');
                    end
                    fprintf('Valid Hub %d: C=(%.1f,%.1f), R=%.1f, DF=%.2f, 4 blobs.\n', ...
                            validHubCount, c(1), c(2), r, darkFraction);
                end
            else
                % Candidate hub with correct darkFraction but not 4 blobs
                if DEBUG
                    viscircles(c, r, 'Color','r','LineStyle','--');
                    text(c(1), c(2)+5, sprintf('Fail: %d blobs', numBlobs), ...
                         'Color','r','FontWeight','bold','FontSize',9);
                    fprintf('Candidate hub (%.1f,%.1f), R=%.1f => %d blobs (DF=%.2f)\n', ...
                            c(1), c(2), r, numBlobs, darkFraction);
                end
            end
        else
            % Dark fraction outside allowed range
            if DEBUG
                viscircles(c, r, 'Color', 'r', 'LineStyle', '--');
                text(c(1), c(2)+5, sprintf('Fail DF=%.2f', darkFraction), ...
                     'Color','r','FontWeight','bold','FontSize',9);
                fprintf('Circle filtered out: (%.1f,%.1f), R=%.1f, DF=%.2f\n', ...
                        c(1), c(2), r, darkFraction);
            end
        end
    end
end
