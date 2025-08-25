import pytesseract
from PIL import Image

img = Image.open("Screenshot 2025-08-24 101240.png")
text = pytesseract.image_to_string(img, lang="eng")
print(text)