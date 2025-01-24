import os
import csv
import subprocess
import sys
from xml.etree import ElementTree as ET
import re

def install_prerequisites():
    try:
        print("Installing prerequisites...")
        pass
    except ImportError:
        print("Installing missing packages...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])

def parse_sval_file(file_path):
    print(f"Attempting to parse file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except FileNotFoundError:
        print(f"Error: File not found - {file_path}")
        return []
    except IOError as e:
        print(f"Error reading file {file_path}: {e}")
        return []

    wrapped_content = f"<root>{content}</root>"
    try:
        root = ET.fromstring(wrapped_content)
    except ET.ParseError as e:
        print(f"Error parsing {file_path}: {e}")
        return []

    array = root.find('array')
    if array is None:
        print(f"No <array> found in {file_path}.")
        return []

    parsed_data = []
    for item in array.findall('dict'):
        data = {}
        for element in item:
            tag_name = element.tag
            name_attr = element.get('name', None)
            text_content = element.text.strip() if element.text else None

            # Handle icon data specially
            if name_attr == "icon":
                # Extract icon data using the same pattern as sprite_slicer.py
                icon_pattern = r'<a name="icon"><s>(.*?)</s><i>\d+</i><vec4>(.*?)</vec4></a>'
                icon_match = re.search(icon_pattern, ET.tostring(element, encoding='unicode'))
                if icon_match:
                    data['spritesheet'] = icon_match.group(1)
                    data['coordinates'] = [int(x) for x in icon_match.group(2).split()]
            elif name_attr and not name_attr.isdigit():
                data[name_attr.lower()] = text_content.strip() if text_content else None
        if data:
            parsed_data.append(data)
    print(f"Parsed {len(parsed_data)} items from {file_path}")
    return parsed_data

def parse_sets_sval(file_path):
    print(f"Attempting to parse sets file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except FileNotFoundError:
        print(f"Error: File not found - {file_path}")
        return [], {}
    except IOError as e:
        print(f"Error reading file {file_path}: {e}")
        return [], {}

    wrapped_content = f"<root>{content}</root>"
    try:
        root = ET.fromstring(wrapped_content)
    except ET.ParseError as e:
        print(f"Error parsing {file_path}: {e}")
        return [], {}

    sets_data = {}
    set_rows = []

    # Cache all .sval files for lookups
    sval_files = find_sval_files(os.path.dirname(file_path))
    all_items = {}
    item_to_set_map = {}
    for sval_file in sval_files:
        parsed_items = parse_sval_file(sval_file)
        for item in parsed_items:
            if "id" in item and "name" in item:
                all_items[item["id"].lower()] = item["name"]
                item_to_set_map[item["id"].lower()] = item

    for set_dict in root.findall('./array/dict'):
        set_id_elem = set_dict.find('string[@name="id"]')
        set_name_elem = set_dict.find('string[@name="name"]')

        set_id = set_id_elem.text.strip().lower() if set_id_elem is not None else None
        set_name = set_name_elem.text.strip() if set_name_elem is not None else None

        items_array = set_dict.find('array[@name="items"]')
        item_ids = [
            item.text.strip().lower() for item in items_array.findall('string') if item.text
        ] if items_array is not None else []

        item_names = [all_items.get(item_id, "Unknown Item") for item_id in item_ids]
        items_in_set = len(item_ids)

        set_effects = []
        for idx, effect_dict in enumerate(set_dict.findall('./dict[@name]')):
            effect_id = effect_dict.get('name', None)
            effect_desc_elem = effect_dict.find('string[@name="desc"]')
            effect_desc = effect_desc_elem.text.strip() if effect_desc_elem is not None else "<No description found>"
            print(f"Debug: Effect ID {effect_id} has description: {effect_desc}")
            if effect_id:
                set_effects.append(f"{effect_id}:{effect_desc}")

        if set_id and set_name:
            print(f"Debug: Found set - ID: {set_id}, Name: {set_name}")
            set_row = {
                "Item Set Name": set_name,
                "Items in Set": items_in_set,
                "Set Items": "\n".join(item_names),
                "Set Effect": "\n\n".join(set_effects)
            }
            set_rows.append(set_row)

            for item_id in item_ids:
                sets_data[item_id] = {
                    "Item Set Name": set_name,
                    "Set Item": True
                }
    print(f"Parsed {len(set_rows)} sets from {file_path}")
    return set_rows, sets_data

def find_sval_files(directory):
    print(f"Searching for .sval files in directory: {directory}")
    sval_files = []
    for root, _, files in os.walk(directory):
        sval_files.extend(os.path.join(root, file) for file in files if file.endswith('.sval'))
    print(f"Found {len(sval_files)} .sval files")
    return sval_files

def get_icon_path(item_id):
    """Check if an icon exists for the given item ID and return its path"""
    current_directory = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(current_directory, "SpritesheetAutoSlicer", "output_sprites", f"{item_id}.png")
    if os.path.exists(icon_path):
        return f"[[File:{item_id}.png]]"  # MediaWiki format for images
    return ""

def write_to_csv(data, output_file, set_rows, sets_data):
    print(f"Writing parsed data to {output_file}")
    if not data and not set_rows:
        print("No data to write.")
        return

    # First pass: collect all possible keys from all items
    all_keys = set()
    for row in data:
        all_keys.update(row.keys())
    
    # Add set-related keys and icon that might not be in the raw data
    all_keys.add("Set Item")
    all_keys.add("Item Set Name")
    all_keys.add("icon")
    all_keys.add("spritesheet")
    all_keys.add("coordinates")
    
    # Convert to sorted list for consistent column order
    column_order = sorted(all_keys)

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=column_order)
            writer.writeheader()

            # Write each row, ensuring all columns are present
            for row in data:
                # Create a new dict with all possible keys initialized to None
                full_row = {key: None for key in column_order}
                
                # Update with actual data from the row
                full_row.update(row)
                
                # Add set information
                item_id = row.get("id", "")
                if item_id in sets_data:
                    print(f"Debug: Match found - Updating '{row.get('name', 'Unknown')}' with set data: {sets_data[item_id]}")
                    full_row.update(sets_data[item_id])
                else:
                    print(f"Debug: No match - '{row.get('name', 'Unknown')}' is not part of any set.")
                    full_row["Set Item"] = False
                    full_row["Item Set Name"] = None
                
                # Convert coordinates to string if present
                if full_row.get("coordinates"):
                    full_row["coordinates"] = " ".join(str(x) for x in full_row["coordinates"])
                
                # Add icon path if available
                full_row["icon"] = get_icon_path(item_id)

                writer.writerow(full_row)
    except IOError as e:
        print(f"Error writing to file {output_file}: {e}")


def write_sets_to_csv(set_rows, output_file):
    print(f"Writing sets data to {output_file}")
    if not set_rows:
        print("No sets to write.")
        return

    preferred_order = ["Item Set Name", "Items in Set", "Set Items", "Set Effect"]

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=preferred_order)
            writer.writeheader()
            for row in set_rows:
                writer.writerow(row)
    except IOError as e:
        print(f"Error writing to file {output_file}: {e}")

def main():
    print("Starting main process...")
    install_prerequisites()
    current_directory = os.path.dirname(os.path.abspath(__file__))
    output_csv = os.path.join(current_directory, "trinket_data.csv")
    sets_csv = os.path.join(current_directory, "trinket_sets_data.csv")
    sets_file = os.path.join(current_directory, "sets.sval")
    set_rows, sets_data = parse_sets_sval(sets_file) if os.path.exists(sets_file) else ([], {})
    sval_files = find_sval_files(current_directory)
    if not sval_files:
        print("No .sval files found in the current directory.")
        return

    # Create a dictionary to track processed items by ID to prevent duplicates
    processed_items = {}
    
    for sval_file in sval_files:
        if os.path.basename(sval_file) == "sets.sval":
            continue  # Skip processing sets.sval directly
        print(f"Parsing {sval_file}...")
        file_data = parse_sval_file(sval_file)
        if file_data:
            # Only add items we haven't seen before
            for item in file_data:
                item_id = item.get('id')
                if item_id and item_id not in processed_items:
                    processed_items[item_id] = item

    # Convert dictionary back to list for writing
    all_data = list(processed_items.values())

    if all_data or set_rows:
        write_to_csv(all_data, output_csv, set_rows, sets_data)
        write_sets_to_csv(set_rows, sets_csv)
        print(f"Data written to {output_csv}")
        print(f"Set bonuses written to {sets_csv}")
    else:
        print("No valid data extracted from the .sval files.")

if __name__ == "__main__":
    main()
