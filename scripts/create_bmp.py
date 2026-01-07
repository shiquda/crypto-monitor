from PIL import Image
import os

def create_bmp_resources():
    # Source image path (using the main logo)
    source_path = os.path.join("imgs", "crypto-monitor.png")
    
    # Ensure source exists
    if not os.path.exists(source_path):
        print(f"Error: Source image not found at {source_path}")
        return

    try:
        img = Image.open(source_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Inno Setup Recommended Sizes:
        # WizardImageFile: 164x314 (Standard)
        # WizardSmallImageFile: 55x58 (Standard)
        
        # Create output directory
        output_dir = os.path.join("assets", "imgs")
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. WizardImageFile (Large left-side image)
        # Resize maintaining aspect ratio, then center crop or pad
        target_size_large = (164, 314)
        large_img = img.resize(target_size_large, Image.Resampling.LANCZOS)
        large_img.save(os.path.join(output_dir, "wizard_large.bmp"), "BMP")
        print(f"Created {os.path.join(output_dir, 'wizard_large.bmp')}")
        
        # 2. WizardSmallImageFile (Top-right small image)
        target_size_small = (55, 58)
        small_img = img.resize(target_size_small, Image.Resampling.LANCZOS)
        small_img.save(os.path.join(output_dir, "wizard_small.bmp"), "BMP")
        print(f"Created {os.path.join(output_dir, 'wizard_small.bmp')}")
        
    except Exception as e:
        print(f"Error converting images: {e}")

if __name__ == "__main__":
    create_bmp_resources()
