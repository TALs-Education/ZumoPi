function hubs = detectHubs(img, DEBUG, thresholdLevel, circleDiameter, expectedDarkFraction, minBlobArea)
% detectHubs Detects circular hubs with LED markers in an image.
%
%   hubs = detectHubs(img, DEBUG, thresholdLevel, circleDiameter, expectedDarkFraction, minBlobArea)
%
%   Processes the input RGB image to identify candidate circular hubs and
%   validates those having exactly 4 LED markers (blobs). In addition to a
%   grayscale threshold, this function adjusts the binary image using the
%   knowledge that the hub is black and the surrounding is blue.
%
%   Input arguments:
%     img                  - Input RGB image.
%     DEBUG                - Boolean flag to display debug plots and print debug info.
%     thresholdLevel       - Grayscale threshold for binarization (default: 0.30).
%     circleDiameter       - Diameter for circle detection (default: 100). (Expected hub size ±25%).
%     expectedDarkFraction - Expected dark fraction inside a hub (default: 0.75). Allowed range ±25%.
%     minBlobArea          - Minimum area (in pixels) for a blob to be considered valid (default: 100).
%
%   Output:
%     hubs - Structure array containing parameters for each valid hub:
%            hub.center, hub.radius, hub.numBlobs, hub.darkFraction, and for each blob:
%            blob#.center and blob#.color.
%
%   Example:
%     img = imread('Image3.jpg');
%     hubs = detectHubs(img, true, 0.30, 100, 0.75, 200);

    % Set default parameter values if not provided
    if nargin < 6, minBlobArea = 100; end
    if nargin < 5, expectedDarkFraction = 0.75; end
    if nargin < 4, circleDiameter = 100; end
    if nargin < 3, thresholdLevel = 0.30; end
    if nargin < 2, DEBUG = false; end

    %% 1. Resize image if larger than 1280x720
    [origH, origW, ~] = size(img);
    maxW = 1280; maxH = 720;
    if origW > maxW || origH > maxH
        scale = min(maxW/origW, maxH/origH);
        img = imresize(img, scale);
        if DEBUG
            fprintf('Image resized from (%d, %d) to (%d, %d)\n', origH, origW, size(img,1), size(img,2));
        end
    end

    %% 2. Convert to grayscale and threshold
    grayImg = rgb2gray(img);
    binImg = imbinarize(grayImg, thresholdLevel);
    binImg = ~binImg;  % Invert so that dark areas become white

    % --- Color-based Adjustment ---
    % Force pixels that are likely blue (i.e. with B significantly higher than R and G) to 0.
    delta = 20;  
    R = double(img(:,:,1)); 
    G = double(img(:,:,2)); 
    B = double(img(:,:,3));
    blueMask = (B - R > delta) & (B - G > delta);
    binImg(blueMask) = 0;

    if DEBUG
        figure; imshow(binImg);
        title('Binary Image (Inverted & Color Adjusted)');
    end

    %% 3. Detect circles (candidate hubs) using imfindcircles
    % Convert the diameter to radius. The allowed radius range is ±25% of the nominal.
    minRadius = floor((circleDiameter * 0.75) / 2);
    maxRadius = floor((circleDiameter * 1.25) / 2);
    [centers, radii, ~] = imfindcircles(binImg, [minRadius, maxRadius], ...
        'ObjectPolarity', 'bright', 'Sensitivity', 0.9);

    if DEBUG
        figure; imshow(img); hold on;
        title('Detected Hubs (Valid in green; Failed in dashed red)');
    end

    %% 4. Initialize structure for valid hubs
    hubs = struct('center',{}, 'radius',{}, 'numBlobs',{}, 'darkFraction',{}, ...
                  'blob1',{}, 'blob2',{}, 'blob3',{}, 'blob4',{});
    validHubCount = 0;
    
    % Compute allowed dark fraction range based on expected value ±25%
    darkFracMin = expectedDarkFraction * 0.75;
    darkFracMax = expectedDarkFraction * 1.25;

    %% 5. Process each candidate hub
    for i = 1:length(radii)
        c = centers(i, :);
        r = radii(i);

        % Create circular mask for candidate hub.
        [X, Y] = meshgrid(1:size(binImg,2), 1:size(binImg,1));
        circleMask = ((X - c(1)).^2 + (Y - c(2)).^2) <= r^2;

        % Compute dark fraction inside the candidate hub.
        whiteCount = sum(binImg(circleMask), 'all');
        circleArea = sum(circleMask(:));
        darkFraction = whiteCount / circleArea;

        if darkFraction >= darkFracMin && darkFraction <= darkFracMax
            % --- LED Blob Detection within the candidate hub ---
            % Set pixels outside the hub to white.
            hubSubImage = binImg;
            hubSubImage(~circleMask) = 1;
            % In the hub region, LED markers appear as black.
            blackRegion = (hubSubImage == 0);

            % Detect connected components (8-connected) in the black region.
            CC = bwconncomp(blackRegion, 8);
            stats = regionprops(CC, 'Centroid', 'Area');

            validCentroids = [];
            validColors = {};
            colorThreshold = 30;  % Used for color similarity

            for j = 1:length(stats)
                if stats(j).Area >= minBlobArea
                    validCentroids = [validCentroids; stats(j).Centroid]; %#ok<AGROW>
                    blobIndices = CC.PixelIdxList{j};

                    % Compute mean color values for the blob.
                    meanR = mean(R(blobIndices));
                    meanG = mean(G(blobIndices));
                    meanB = mean(B(blobIndices));

                    % Classify blob color.
                    if abs(meanR - meanG) < colorThreshold && abs(meanR - meanB) < colorThreshold && abs(meanG - meanB) < colorThreshold
                        blobColor = 'white';
                    elseif meanR > meanG && meanR > meanB
                        blobColor = 'red';
                    elseif meanG > meanR && meanG > meanB
                        blobColor = 'green';
                    elseif meanB > meanR && meanB > meanG
                        blobColor = 'blue';
                    else
                        blobColor = 'unknown';
                    end
                    validColors{end+1} = blobColor;
                end
            end

            numBlobs = size(validCentroids, 1);

            % --- Hub Validation: Require exactly 4 LED markers ---
            if numBlobs == 4
                % Sort the 4 blobs in clockwise order (starting from "up").
                angles = zeros(numBlobs, 1);
                for k = 1:numBlobs
                    dX = validCentroids(k,1) - c(1);
                    dY = validCentroids(k,2) - c(2);
                    angles(k) = mod(atan2(dX, -dY), 2*pi);
                end
                [~, sortOrder] = sort(angles);
                sortedCentroids = validCentroids(sortOrder, :);
                sortedColors = validColors(sortOrder);

                validHubCount = validHubCount + 1;
                hubs(validHubCount).center = c;
                hubs(validHubCount).radius = r;
                hubs(validHubCount).numBlobs = numBlobs;
                hubs(validHubCount).darkFraction = darkFraction;
                for k = 1:numBlobs
                    fieldName = sprintf('blob%d', k);
                    hubs(validHubCount).(fieldName).center = sortedCentroids(k, :);
                    hubs(validHubCount).(fieldName).color = sortedColors{k};
                end

                if DEBUG
                    viscircles(c, r, 'Color', 'g');
                    plot(c(1), c(2), 'gx', 'MarkerSize', 12, 'LineWidth', 2);
                    for k = 1:numBlobs
                        blobLetter = upper(sortedColors{k}(1));
                        blobPos = sortedCentroids(k, :);
                        text(blobPos(1), blobPos(2), blobLetter, 'Color', 'k', ...
                             'FontSize', 14, 'FontWeight', 'bold', 'HorizontalAlignment','center');
                    end
                    fprintf('Valid Hub %d: Center=(%.1f, %.1f), Radius=%.1f, DarkFraction=%.2f, 4 blobs detected.\n', ...
                        validHubCount, c(1), c(2), r, darkFraction);
                end
            else
                if DEBUG
                    viscircles(c, r, 'Color', 'r', 'LineStyle', '--');
                    text(c(1), c(2)+5, sprintf('Fail: %d blobs', numBlobs), 'Color', 'r', ...
                         'FontWeight', 'bold', 'FontSize', 9);
                    fprintf('Candidate hub at (%.1f, %.1f) with radius=%.1f failed: %d blobs detected (DarkFraction=%.2f).\n', ...
                        c(1), c(2), r, numBlobs, darkFraction);
                end
            end
        else
            if DEBUG
                viscircles(c, r, 'Color', 'r', 'LineStyle', '--');
                text(c(1), c(2)+5, sprintf('Fail DF: %.2f', darkFraction), 'Color', 'r', ...
                     'FontWeight', 'bold', 'FontSize', 9);
                fprintf('Circle filtered out: Center=(%.1f, %.1f), Radius=%.1f, DarkFraction=%.2f\n', ...
                        c(1), c(2), r, darkFraction);
            end
        end
    end
end
