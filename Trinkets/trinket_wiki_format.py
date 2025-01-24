import os
import csv
from collections import defaultdict
import re

# Configuration variables for easy tuning
DESCRIPTION_WRAP_LIMIT = 40  # Max characters per line before wrapping
CELL_PADDING = "10px"  # Padding for regular table cells
ICON_PADDING = "15px"  # Padding for icon column
ICON_SIZE = 32  # Size in pixels for icon images (default sprite size is 24px)
INLINE_ICON_SIZE = 16  # Size in pixels for inline icons next to item names
SET_ICON_SIZE = 24  # Size in pixels for icons displayed under set names
MAIN_HEADER_FONT_SIZE = "16px"  # Font size for the main table header
COLUMN_HEADER_FONT_SIZE = "15px"  # Font size for column headers
NAME_FONT_SIZE = "14px"   # Font size for item names
DESC_FONT_SIZE = "14px"   # Font size for descriptions
CELL_FONT_SIZE = "14px"   # Font size for other cells
SET_NAME_FONT_SIZE = "16px"  # Font size for set names in the sets table
NO_ATTUNEMENT_STYLE_LIGHTNESS = 0.3  # Lightness adjustment for "No Attunement" text color

# Dictionary for MediaWiki link terms
MEDIAWIKI_LINKS = {
    # Vitals
    "Health": "Combat#Health|Health",
    "Mana": "Combat#Mana|Mana",
    "Regeneration": "Combat|Regeneration",
    
    # Damage stuff
    "Attack Power": "Combat|Attack Power",
    "Crit Chance": "Combat|Crit Chance",
    "Spell Power": "Combat|Spell Power",
    "Spell Crit": "Combat|Spell Crit",
    "Penetration": "Combat|Penetration",
    "Cast Speed": "Combat|Cast Speed",
    "Weapon Speed": "Combat|Weapon Speed",
    "Damage": "Combat|Damage",
    
    # Mechanics
    "Spells": "Combat|Spells",
    "Weapon Attacks": "Combat|Weapon Attacks",
    "Movement Speed": "Combat|Movement Speed",
    "Dash": "Combat|Dash",
    "Evasion": "Combat|Evasion",
    "Parry": "Combat|Parry",
    "Debuff": "Combat|Debuff",
    "Potion": "Combat|Potion",
    "Shadow Curse Gain": "Mechanics|Shadow Curse Gain",
    "Shadow Curse": "Mechanics|Shadow Curse",
    
    # Armor stuff
    "Armor": "Combat|Armor",
    "Resistance": "Combat|Resistance",
    "Resistances": "Combat|Resistance",
    
    # Progression stuff
    "Experience": "Leveling_Up#Experience|Experience",
    "Gold": "Currencies#Gold|Gold",
    "Stone": "Materials#Stone|Stone",
    "Wood": "Materials#Wood|Wood",
    "Metal": "Materials#Metal|Metal",
    
    # Elements & Damage Types
    "Physical": "Combat|Physical",
    "Poison": "Combat|Poison",
    "Fire": "Combat|Fire",
    "Ice": "Combat|Ice",
    "Lightning": "Combat|Lightning",
    
    # Status Effect stuff
    "Stun": "Combat|Stun",
    "Bleeding": "Combat|Bleeding",
    "Slow": "Combat|Slow",
    "Cripple": "Combat|Cripple",
    "Confusion": "Combat|Confusion",
    
    # Items
    "Weapon": "Equipment#Weapons|Weapon"
}

# Color and style settings
quality_styles = {
    "common": ["#262626", "#212121"],
    "uncommon": ["#283a33", "#1d2622"],
    "rare": ["#1d2335", "#181a23"],
    "epic": ["#33283a", "#221d26"],
    "cursed": ["#3a2828", "#261d1d"]
}

name_colors = {
    "common": "#bababa",
    "uncommon": "#00dc00",
    "rare": "#33ccff",
    "epic": "#c975fc",
    "cursed": "red"
}

# Helper functions
def get_row_style(quality, index):
    styles = quality_styles.get(quality, ["White", "#F0F0F0"])
    return styles[index % 2]

def get_lighter_color(color):
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    r = min(255, int(r + (255 - r) * NO_ATTUNEMENT_STYLE_LIGHTNESS))
    g = min(255, int(g + (255 - g) * NO_ATTUNEMENT_STYLE_LIGHTNESS))
    b = min(255, int(b + (255 - b) * NO_ATTUNEMENT_STYLE_LIGHTNESS))
    return f"#{r:02x}{g:02x}{b:02x}"

def word_wrap(text, limit=DESCRIPTION_WRAP_LIMIT):
    # Split into lines first
    lines = []
    current_line = ""
    words = text.split()
    
    for i, word in enumerate(words):
        # Check if this word starts with "+ " and it's not the first word
        if word.startswith("+") and i > 0:
            # Add the current line if it's not empty
            if current_line:
                lines.append(current_line.strip())
            current_line = word
        else:
            # Add word to current line if it fits
            if len(current_line) + len(word) + 1 <= limit:
                if current_line:
                    current_line += " "
                current_line += word
            else:
                # Line is full, start a new one
                lines.append(current_line.strip())
                current_line = word
    
    # Add the last line if not empty
    if current_line:
        lines.append(current_line.strip())
    
    # Join lines with <br>
    return "<br>".join(lines)

def apply_mediawiki_links(text, linked_terms=set()):
    # Sort terms by length descending to prioritize longer matches
    sorted_terms = sorted(MEDIAWIKI_LINKS.items(), key=lambda x: -len(x[0]))
    
    # Keep track of positions that are already part of a link
    linked_positions = set()
    
    # First pass: find all matches and their positions
    matches = []
    for term, link in sorted_terms:
        for match in re.finditer(rf"\b{re.escape(term)}\b", text):
            start, end = match.span()
            # Check if this match overlaps with any existing linked positions
            if not any(pos in linked_positions for pos in range(start, end)):
                matches.append((start, end, term, link))
                # Mark these positions as linked
                linked_positions.update(range(start, end))
    
    # Sort matches by start position in reverse order (to maintain string indices when replacing)
    matches.sort(key=lambda x: x[0], reverse=True)
    
    # Second pass: apply the replacements from end to start
    for start, end, term, link in matches:
        text = text[:start] + f"[[{link}]]" + text[end:]
        linked_terms.add(term)
    
    return text

def apply_color_coding(text):
    # Remove color formatting codes, keeping only the content
    # Match the exact pattern: \c followed by b, then exactly 5 hex digits, then content, then \d
    return re.sub(r"\\cb([0-9a-fA-F]{5})([^\\]+)\\d", r"\2", text)

def split_description(description, row_style):
    base_desc = ""
    attuned_desc = f"<i style=\"color:{get_lighter_color(row_style)};\">No Attunement</i>"
    linked_terms = set()

    if "Base:" in description:
        base_start = description.find("Base:") + len("Base:")
        base_end = description.find("Attuned:") if "Attuned:" in description else len(description)
        base_desc = description[base_start:base_end].strip().replace("\n", " ")
        base_desc = word_wrap(base_desc)
        # First remove color formatting, then apply MediaWiki links
        base_desc = apply_color_coding(base_desc)
        base_desc = apply_mediawiki_links(base_desc, linked_terms)

    if "Attuned:" in description:
        attuned_start = description.find("Attuned:") + len("Attuned:")
        attuned_desc = description[attuned_start:].strip().replace("\n", " ")
        attuned_desc = word_wrap(attuned_desc)
        # First remove color formatting, then apply MediaWiki links
        attuned_desc = apply_color_coding(attuned_desc)
        attuned_desc = apply_mediawiki_links(attuned_desc, linked_terms)

    return base_desc, attuned_desc

def process_raw_description(row):
    """Convert raw description fields into formatted description"""
    desc = row.get("desc", "")
    attune_desc = row.get("attune-desc", "")
    
    description = ""
    if desc:
        description += "Base: " + desc.replace("\\n", "\n")
    if attune_desc:
        if description:
            description += "\n\n"
        description += "Attuned: " + attune_desc.replace("\\n", "\n")
    return description

def filter_row_data(row):
    """Filter and transform raw row data into wiki format"""
    # Define the columns we want in the wiki output
    wiki_columns = ["icon", "name", "description", "price", "quality", "Set Item", "Item Set Name"]
    filtered_row = {}
    
    # Process description fields
    filtered_row["description"] = process_raw_description(row)
    
    # Copy other desired fields
    for col in wiki_columns:
        if col != "description" and col in row:
            filtered_row[col] = row[col] if row[col] is not None else ""
            
    return filtered_row

def generate_wiki_tables(data):
    # Group data by quality
    grouped_data = defaultdict(list)
    for row in data:
        wiki_row = filter_row_data(row)
        grouped_data[row['quality'].lower()].append(wiki_row)

    # Generate tables
    for quality, items in grouped_data.items():
        quality_title = f"List of {quality.capitalize()} Trinkets"
        
        # Start table with header
        table_output = [
            "{| class=\"wikitable\" style=\"border-collapse:collapse;\"",
            f"! colspan=\"7\" style=\"font-size:{MAIN_HEADER_FONT_SIZE}; padding:8px;\" | {quality_title}",
            "|-",
            ""
        ]
        
        # Add column headers
        headers = ["Icon", "Name", "Base Description", "Attuned Description", "Price", "Set Item", "Item Set Name"]
        header_cells = [f"! style=\"font-size:{COLUMN_HEADER_FONT_SIZE}; padding:5px;\" | '''{header.title()}'''" for header in headers]
        table_output.append(" !! ".join(header_cells))
        
        # Add rows for each item
        for index, row in enumerate(items):
            table_output.extend([
                "|-",
                ""
            ])
            
            row_style = get_row_style(quality, index)
            name_color = name_colors.get(quality, "black")
            base_desc, attuned_desc = split_description(row['description'], row_style)
            set_item = "" if row.get('Set Item', '').lower() == 'false' else "✔"
            
            # Format the icon
            icon = row.get('icon', '')
            if icon:
                icon = icon.replace("[[File:", f"[[File:")
                icon = icon[:-2] + f"|{ICON_SIZE}px]]"
            
            # Add link to set name if it exists
            set_name = row.get('Item Set Name', '')
            if set_name:
                set_name = f"[[#{set_name.replace(' ', '_').lower()}|{set_name}]]"
            
            # Format each cell with proper indentation
            cells = [
                f"| style=\"text-align:center; padding:{ICON_PADDING};\" | {icon}",
                f"| style=\"text-align:center; background-color:{row_style}; color:{name_color}; padding:{CELL_PADDING}; font-size:{NAME_FONT_SIZE};\" | <span id=\"{row['name'].replace(' ', '_').lower()}\">{row['name']}</span>",
                f"| style=\"text-align:center; background-color:{row_style}; padding:{CELL_PADDING}; font-size:{DESC_FONT_SIZE};\" | {base_desc}",
                f"| style=\"text-align:center; background-color:{row_style}; padding:{CELL_PADDING}; font-size:{DESC_FONT_SIZE};\" | {attuned_desc}",
                f"| style=\"text-align:center; background-color:{row_style}; padding:{CELL_PADDING}; font-size:{CELL_FONT_SIZE};\" | {row.get('price', '')}",
                f"| style=\"text-align:center; background-color:{row_style}; padding:{CELL_PADDING}; font-size:{CELL_FONT_SIZE};\" | {set_item}",
                f"| style=\"background-color:{row_style}; padding:{CELL_PADDING}; font-size:{CELL_FONT_SIZE};\" | {set_name}"
            ]
            table_output.extend(cells)
            table_output.append("")
        
        # End the table
        table_output.extend([
            "|}",
            ""
        ])
        
        # Save each table to a separate file
        table_file_path = os.path.join(os.path.dirname(__file__), f"{quality}_trinkets_table.txt")
        with open(table_file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(table_output))

def load_trinket_data():
    """Load the raw trinket data from CSV"""
    current_directory = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_directory, 'trinket_data.csv')
    sets_csv_path = os.path.join(current_directory, 'trinket_sets_data.csv')
    
    data = []
    sets_data = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            data = list(reader)
    except FileNotFoundError:
        print(f"Error: trinket_data.csv not found in {current_directory}")
    except Exception as e:
        print(f"Error reading trinket_data.csv: {e}")
    
    try:
        with open(sets_csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            sets_data = list(reader)
    except FileNotFoundError:
        print(f"Error: trinket_sets_data.csv not found in {current_directory}")
    except Exception as e:
        print(f"Error reading trinket_sets_data.csv: {e}")
    
    return data, sets_data

def format_set_items(set_items, trinket_data):
    """Format set items with their quality colors and inline icons"""
    # Create mappings of item names to their qualities and icons
    item_data = {
        item['name']: {
            'quality': item['quality'].lower(),
            'icon': item.get('icon', '')
        } for item in trinket_data
    }
    
    items = set_items.split('\n')
    formatted_items = []
    
    for item in items:
        item = item.strip()
        if item:
            data = item_data.get(item, {'quality': 'common', 'icon': ''})
            quality = data['quality']
            color = name_colors.get(quality, '#bababa')
            
            # Format the icon with size parameter
            icon = data['icon']
            if icon:
                icon = icon.replace("[[File:", "[[File:")
                icon = icon[:-2] + f"|{INLINE_ICON_SIZE}px]]"  # Insert size before closing brackets
            
            # Create link to the item in its quality table using the item's name as anchor
            item_anchor = item.replace(' ', '_').lower()
            formatted_items.append(
                f"{icon} <span style=\"color:{color}; vertical-align:middle;\">[[#{item_anchor}|{item}]]</span>"
            )
    
    return "<br>".join(formatted_items)

def format_set_effects(set_effects):
    """Format set effects as a sub-table"""
    if not set_effects:
        return ""
    
    effects = set_effects.split('\n\n')
    if not effects:
        return ""
    
    # Create rows for each effect without using a nested table
    rows = []
    for effect in effects:
        if ':' not in effect:
            continue
            
        num_items, description = effect.split(':', 1)
        # Apply MediaWiki links to the description
        linked_description = apply_mediawiki_links(description.strip())
        
        rows.append(
            f"<div style=\"display:flex; width:100%; margin:2px 0;\">"
            f"<div style=\"width:80px; text-align:right; font-weight:bold; padding-right:5px;\">{num_items} items:</div>"
            f"<div style=\"flex:1; text-align:left; padding-left:5px;\">{linked_description}</div>"
            f"</div>"
        )
    
    return "<div style=\"width:100%;\">" + "".join(rows) + "</div>"

def get_set_icons(set_items, trinket_data, size=None):
    """Get formatted icons for all items in a set"""
    # Use SET_ICON_SIZE by default
    if size is None:
        size = SET_ICON_SIZE
        
    # Create mapping of item names to their icons
    item_data = {item['name']: item.get('icon', '') for item in trinket_data}
    
    icons = []
    items = set_items.split('\n')
    for item in items:
        item = item.strip()
        if item and item in item_data:
            icon = item_data[item]
            if icon:
                icon = icon.replace("[[File:", "[[File:")
                icon = icon[:-2] + f"|{size}px]]"  # Insert size before closing brackets
                icons.append(icon)
    
    return " ".join(icons) if icons else ""

def generate_sets_table(sets_data, trinket_data):
    """Generate a table for trinket sets"""
    # Start table with header
    table_output = [
        "{| class=\"wikitable\" style=\"border-collapse:collapse;\"",
        f"! colspan=\"4\" style=\"font-size:{MAIN_HEADER_FONT_SIZE}; padding:8px;\" | Trinket Sets",
        "|-",
        ""
    ]
    
    # Add column headers
    headers = ["Set Name", "Items in Set", "Set Items", "Set Effects"]
    header_cells = [f"! style=\"font-size:{COLUMN_HEADER_FONT_SIZE}; padding:5px;\" | '''{header}'''" for header in headers]
    table_output.append(" !! ".join(header_cells))
    
    # Add rows for each set
    for index, row in enumerate(sets_data):
        table_output.extend([
            "|-",
            ""
        ])
        
        row_style = quality_styles['common'][index % 2]
        
        # Format set items with quality colors and inline icons
        formatted_items = format_set_items(row.get('Set Items', ''), trinket_data)
        
        # Get set icons
        set_icons = get_set_icons(row.get('Set Items', ''), trinket_data)
        
        # Format set name with icons underneath and add anchor
        set_name = row.get('Item Set Name', '')
        set_name_anchor = set_name.replace(' ', '_').lower()
        set_name_cell = (
            f"<span id=\"{set_name_anchor}\">{set_name}</span><br><br>"
            f"{set_icons}"
        )
        
        # Format set effects as sub-table
        set_effects = format_set_effects(row.get('Set Effect', ''))
        
        # Format each cell with proper indentation
        cells = [
            f"| style=\"text-align:center; background-color:{row_style}; padding:{CELL_PADDING}; font-size:{SET_NAME_FONT_SIZE};\" | {set_name_cell}",
            f"| style=\"text-align:center; background-color:{row_style}; padding:{CELL_PADDING}; font-size:{CELL_FONT_SIZE};\" | {row.get('Items in Set', '')}",
            f"| style=\"background-color:{row_style}; padding:{CELL_PADDING}; font-size:{NAME_FONT_SIZE};\" | {formatted_items}",
            f"| style=\"background-color:{row_style}; padding:{CELL_PADDING}; font-size:{DESC_FONT_SIZE};\" | {set_effects}"
        ]
        table_output.extend(cells)
        table_output.append("")
    
    # End the table
    table_output.extend([
        "|}",
        ""
    ])
    
    # Save the sets table
    table_file_path = os.path.join(os.path.dirname(__file__), "trinket_sets_table.txt")
    with open(table_file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(table_output))

def main():
    # Load the raw data
    trinket_data, sets_data = load_trinket_data()
    if not trinket_data:
        print("No trinket data found. Please run trinket_data_extractor.py first.")
        return

    # Generate wiki tables
    generate_wiki_tables(trinket_data)
    if sets_data:
        generate_sets_table(sets_data, trinket_data)
    print("Wiki tables have been generated successfully.")

if __name__ == "__main__":
    main()
