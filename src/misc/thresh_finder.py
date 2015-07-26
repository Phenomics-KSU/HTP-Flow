import cv2
import numpy as np

def nothing(x):
    # get info from track bar and apply to result
    thresh = cv2.getTrackbarPos('thresh','result')
    
    _, thresh_image = cv2.threshold(gray_image, thresh, 255, 0)
    
    #thresh_image = cv2.adaptiveThreshold(gray_image,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,thresh,2)
    
    cv2.imshow("result", thresh_image)

# Creating a window for later use
cv2.namedWindow('result', cv2.CV_WINDOW_AUTOSIZE)

# Creating track bar
cv2.createTrackbar('thresh', 'result', 0,255,nothing)

image = cv2.imread(r"L:\sunflower\day3_7_08_2015\images\cam04_converted\CAM_3671509273_20150708_104841_C04_9659.jpg")

gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
gray_image = cv2.resize(gray_image, (0,0), fx=0.1, fy=0.1) 

cv2.imshow("result", gray_image)

while True:

    if cv2.waitKey(1) & 0xFF == 27:
        break
    
cv2.destroyAllWindows()