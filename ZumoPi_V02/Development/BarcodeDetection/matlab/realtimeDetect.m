%% Real-Time Hub Detection Using Webcam (Print FPS to Command Window)
% Create a webcam object (default camera) and set its resolution.
cam = webcam;
cam.Resolution = "1280x720";

% Set debug display flag:
% If true, the binary (thresholded) image will be shown instead of the color image,
% and a slider with a numeric label is provided to adjust the threshold level in real time.
debugDisplay = false;
thresholdLevel = 0.4;

% Create a figure and axes for streaming.
hFig = figure('Name', 'Real-Time Hub Detection', 'NumberTitle', 'off');
hAx = axes('Parent', hFig);

% If in debug mode, create a slider for threshold adjustment.
if debugDisplay
    % Slider for threshold adjustment
    hSlider = uicontrol('Parent', hFig, 'Style', 'slider', 'Units', 'normalized',...
        'Position', [0.1 0.01 0.6 0.05], 'Min', 0, 'Max', 1, 'Value', thresholdLevel);
    % A label to show threshold value
    hSliderLabel = uicontrol('Parent', hFig, 'Style', 'text', 'Units', 'normalized',...
        'Position', [0.72 0.01 0.15 0.05], 'FontSize', 12, ...
        'String', sprintf('Threshold: %.2f', thresholdLevel));
end

% Initialize timer for measuring frame intervals
tPrev = tic;

% Continuously capture frames and process them until the figure closes.
while ishandle(hFig)
    % Capture a frame from the webcam
    img = snapshot(cam);

    % Calculate elapsed time and FPS since last frame
    elapsed = toc(tPrev);
    fps = 1 / elapsed;
    tPrev = tic;  % reset for next iteration

    % If debug mode, update threshold from slider
    if debugDisplay
        thresholdLevel = get(hSlider, 'Value');
        set(hSliderLabel, 'String', sprintf('Threshold: %.2f', thresholdLevel));
    end

    % Detect hubs (using your custom detectHubs function)
    hubs = detectHubs(img, false, thresholdLevel, 100, 0.85, 50);

    % Display either the binary image (debug mode) or the original image
    if debugDisplay
        % Convert to grayscale, apply threshold, invert
        grayImg = rgb2gray(img);
        binImg = imbinarize(grayImg, thresholdLevel);
        binImg = ~binImg;

        % Extra color-based adjustment to remove strongly blue areas
        delta = 20;
        R = double(img(:,:,1));
        G = double(img(:,:,2));
        B = double(img(:,:,3));
        blueMask = (B - R > delta) & (B - G > delta);
        binImg(blueMask) = 0;

        imshow(binImg, 'Parent', hAx);
    else
        imshow(img, 'Parent', hAx);
    end
    hold(hAx, 'on');

    % Overlay the detected hubs and their blobs
    for k = 1:length(hubs)
        c = hubs(k).center;    % (x,y)
        r = hubs(k).radius;

        % Draw a green circle for each hub
        viscircles(hAx, c, r, 'Color', 'g');
        % Mark center with a green 'X'
        plot(hAx, c(1), c(2), 'gx', 'MarkerSize', 12, 'LineWidth', 2);

        % Annotate the 4 LED blobs
        for j = 1:4
            fieldName = sprintf('blob%d', j);
            blob = hubs(k).(fieldName);
            blobLetter = upper(blob.color(1));
            text(hAx, blob.center(1), blob.center(2), blobLetter, ...
                'Color', 'k', 'FontSize', 14, 'FontWeight', 'bold', ...
                'HorizontalAlignment', 'center');
        end

        % Print hub data to the command window
        fprintf('Hub %d: Center=(%.1f, %.1f), Radius=%.1f, DF=%.2f, Blobs: ', ...
            k, c(1), c(2), r, hubs(k).darkFraction);
        for j = 1:4
            fieldName = sprintf('blob%d', j);
            fprintf('%s ', hubs(k).(fieldName).color);
        end
        fprintf('\n');
    end

    % Print the FPS in the command window
    fprintf('FPS: %.2f\n', fps);

    hold(hAx, 'off');
    drawnow;
end

% Clear the webcam object when done.
clear cam;
