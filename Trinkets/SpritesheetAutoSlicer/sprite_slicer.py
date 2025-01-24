import os
import csv
from PIL import Image
from pathlib import Path

def read_trinket_data(csv_path):
    """Read trinket data from the CSV file."""
    items = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('spritesheet') and row.get('coordinates'):
                    items.append({
                        'id': row.get('id'),
                        'spritesheet': row.get('spritesheet'),
                        'coordinates': [int(x) for x in row['coordinates'].split()]
                    })
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")
    return items

def crop_sprite(spritesheet_path, coordinates, output_path):
    """Crop a sprite from the spritesheet using the given coordinates."""
    try:
        with Image.open(spritesheet_path) as img:
            x, y, w, h = coordinates
            cropped = img.crop((x, y, x + w, y + h))
            cropped.save(output_path)
    except Exception as e:
        print(f"Error processing {output_path}: {str(e)}")

def main():
    # Create output directory if it doesn't exist
    output_dir = Path("output_sprites")
    output_dir.mkdir(exist_ok=True)
    
    # Read trinket data from CSV
    csv_path = Path("../trinket_data.csv")
    if not csv_path.exists():
        print(f"Error: {csv_path} not found. Please run trinket_data_extractor.py first.")
        return
        
    items = read_trinket_data(csv_path)
    if not items:
        print("No items found in the CSV file.")
        return
    
    # Keep track of processed items to avoid duplicates
    processed_items = set()
    
    for item in items:
        if item['id'] in processed_items:
            continue
            
        processed_items.add(item['id'])
        
        # Determine spritesheet path
        spritesheet_name = os.path.basename(item['spritesheet'])
        spritesheet_path = Path(spritesheet_name)
        
        # Create output path
        output_path = output_dir / f"{item['id']}.png"
        
        print(f"Extracting {item['id']}...")
        crop_sprite(spritesheet_path, item['coordinates'], output_path)

if __name__ == "__main__":
    main() 