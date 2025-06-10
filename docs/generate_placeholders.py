from PIL import Image, ImageDraw, ImageFont
import os

def create_placeholder(width, height, text, output_path):
    # Create a new image with a light gray background
    image = Image.new('RGB', (width, height), color='#f0f0f0')
    draw = ImageDraw.Draw(image)
    
    # Add a border
    draw.rectangle([(0, 0), (width-1, height-1)], outline='#cccccc')
    
    # Add text
    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except:
        font = ImageFont.load_default()
    
    # Center the text
    text_width = draw.textlength(text, font=font)
    text_position = ((width - text_width) // 2, height // 2 - 16)
    
    # Draw text with a shadow
    draw.text((text_position[0]+2, text_position[1]+2), text, fill='#666666', font=font)
    draw.text(text_position, text, fill='#333333', font=font)
    
    # Save the image
    image.save(output_path)

def main():
    # Ensure the images directory exists
    os.makedirs('docs/images', exist_ok=True)
    
    # Create placeholder images
    create_placeholder(800, 400, 'DASHBOARD DEMO — Coming Soon', 'docs/images/dashboard_preview.png')
    create_placeholder(800, 400, 'DISCORD AUTONOMY — Integration Preview', 'docs/images/discord_preview.png')

if __name__ == '__main__':
    main() 