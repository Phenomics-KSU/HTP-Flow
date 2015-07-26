import cv2
import numpy as np
import sys

def nothing(x):
    # get info from track bar and apply to result
    hlow = cv2.getTrackbarPos('hlow','result')
    slow = cv2.getTrackbarPos('slow','result')
    vlow = cv2.getTrackbarPos('vlow','result')
    hhigh = cv2.getTrackbarPos('hhigh','result')
    shigh = cv2.getTrackbarPos('shigh','result')
    vhigh = cv2.getTrackbarPos('vhigh','result')

    # Normal masking algorithm
    lower = np.array([hlow,slow,vlow])
    upper = np.array([hhigh,shigh,vhigh])

    mask = cv2.inRange(hsv,lower, upper)
    
    cv2.imshow("result", mask)

image = cv2.imread(r"L:\sunflower\day3_7_08_2015\images\cam04_converted\CAM_3671509273_20150708_150644_C04_2669.jpg", cv2.CV_LOAD_IMAGE_COLOR)

if image is None:
    print "Image is none"
    sys.exit(1)

#image.convertTo(image, cv2.CV_32F);

# Creating a window for later use
cv2.namedWindow('result', cv2.CV_WINDOW_AUTOSIZE)

# Starting with 100's to prevent error while masking
hlow,slow,vlow = 100,50,50
hhigh,shigh,vhigh = 120,255,255

# Creating track bar
cv2.createTrackbar('hlow', 'result', 0,179,nothing)
cv2.createTrackbar('slow', 'result', 0,255,nothing)
cv2.createTrackbar('vlow', 'result', 0,255,nothing)
cv2.createTrackbar('hhigh', 'result', 0,179,nothing)
cv2.createTrackbar('shigh', 'result', 0,255,nothing)
cv2.createTrackbar('vhigh', 'result', 0,255,nothing)

#converting to HSV
hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
hsv = cv2.resize(hsv, (0,0), fx=0.1, fy=0.1) 

cv2.imshow("result", hsv)

while True:

    if cv2.waitKey(1) & 0xFF == 27:
        break