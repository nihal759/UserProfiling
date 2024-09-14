import cv2
import numpy as np

# Load the image
image = cv2.imread(r"C:\Users\M Tayyeb\OneDrive\Desktop\20210217_114740.jpg")

# Convert to grayscale
gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Invert the grayscale image
inverted_gray_image = cv2.bitwise_not(gray_image)

# Apply Gaussian blur to the inverted image
blurred_image = cv2.GaussianBlur(inverted_gray_image, (21, 21), 0)

# Create the pencil sketch by blending the grayscale image with the blurred inverted image
sketch_image = cv2.divide(gray_image, 255 - blurred_image, scale=256)

# Save or display the result
cv2.imwrite('sketch_image.jpg', sketch_image)
cv2.imshow('Sketch', sketch_image)
cv2.waitKey(0)
cv2.destroyAllWindows()
