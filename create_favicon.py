import os
from PIL import Image, ImageDraw, ImageFont

# Create the directory if it doesn't exist
os.makedirs('staticfiles_build/static', exist_ok=True)

# Create a new image with a white background
img = Image.new('RGB', (32, 32), color='white')

# Get a drawing context
d = ImageDraw.Draw(img)

# Load a font
try:
    font = ImageFont.truetype("arial.ttf", 24)
except IOError:
    font = ImageFont.load_default()

# Draw text on the image
d.text((8, 2), "AI", fill='black', font=font)

# Save the image in the correct directory
img.save('staticfiles_build/static/favicon.ico')

print("Favicon created successfully in staticfiles_build/static/favicon.ico")
