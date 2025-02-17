%% Real-Time Hub Detection Using Webcam (with Debug Display, Adjustable Threshold, and Command Line Hub Data)

% Create a webcam object (default camera) and set its resolution.
cam = webcam;
cam.Resolution = "1280x720";   

% Set debug display flag:
% If true, the binary (thresholded) image will be shown instead of the color image,
% and a slider with a numeric label is provided to adjust the threshold level in real time.
debugDisplay = false;

% Create a figure and an axes for streaming.
hFig = figure('Name', 'Real-Time Hub Detection', 'NumberTitle', 'off');
hAx = axes('Parent', hFig);

% In debug mode, add a slider and a label to adjust the threshold level.
if debugDisplay
    % Slider for threshold adjustment.
    hSlider = uicontrol('Parent', hFig, 'Style', 'slider', 'Units', 'normalized',...
        'Position', [0.1 0.01 0.6 0.05], 'Min', 0, 'Max', 1, 'Value', 0.30);
    % A label to display the current threshold value next to the slider.
    hSliderLabel = uicontrol('Parent', hFig, 'Style', 'text', 'Units', 'normalized',...
        'Position', [0.72 0.01 0.15 0.05], 'FontSize', 12, 'String', 'Threshold: 0.30');
end

% Continuously capture frames and process them.
while ishandle(hFig)
    % Capture a frame from the webcam.
    img = snapshot(cam);
    
    % In debug mode, update the threshold level from the slider.
    if debugDisplay
        thresholdLevel = get(hSlider, 'Value');
        set(hSliderLabel, 'String', sprintf('Threshold: %.2f', thresholdLevel));
        % Call detectHubs with the current thresholdLevel and custom parameters.
        hubs = detectHubs(img, false, thresholdLevel, 25, 0.75, 50);
    else
        hubs = detectHubs(img, false, thresholdLevel, 50, 0.6, 100);
    end
    
    % Display either the binary image (if in debug mode) or the original image.
    if debugDisplay
        % Convert to grayscale, apply threshold and invert.
        grayImg = rgb2gray(img);
        binImg = imbinarize(grayImg, thresholdLevel);
        binImg = ~binImg;
        
        % --- Color-based Adjustment ---
        delta = 20;  % Heuristic threshold difference
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
    
    % Overlay detected hubs and their annotations.
    for k = 1:length(hubs)
         % Get hub center and radius.
         c = hubs(k).center;
         r = hubs(k).radius;
         
         % Draw a green circle around the hub.
         viscircles(hAx, c, r, 'Color', 'g');
         % Mark the hub center with a green X.
         plot(hAx, c(1), c(2), 'gx', 'MarkerSize', 12, 'LineWidth', 2);
         
         % Annotate each of the 4 LED blobs with its color initial (R, G, B, or W).
         for j = 1:4
              fieldName = sprintf('blob%d', j);
              blob = hubs(k).(fieldName);
              blobLetter = upper(blob.color(1));  % Use the first letter.
              text(hAx, blob.center(1), blob.center(2), blobLetter, ...
                  'Color', 'k', 'FontSize', 14, 'FontWeight', 'bold', ...
                  'HorizontalAlignment', 'center');
         end
         
         % Print hub data to the MATLAB command window.
         fprintf('Hub %d: Center=(%.1f, %.1f), Radius=%.1f, DF=%.2f, Blobs: ', ...
                 k, c(1), c(2), r, hubs(k).darkFraction);
         for j = 1:4
              fieldName = sprintf('blob%d', j);
              fprintf('%s ', hubs(k).(fieldName).color);
         end
         fprintf('\n');
    end
    hold(hAx, 'off');
    
    % Update the figure window.
    drawnow;
end

% Clear the webcam object when done.
clear cam;
