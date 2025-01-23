import os
import csv
from collections import defaultdict
import re

# Configuration variables for easy tuning
DESCRIPTION_WRAP_LIMIT = 40  # Max characters per line before wrapping
CELL_PADDING = "10px"  # Padding for table cells
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

# Load the data from the CSV file
current_directory = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_directory, 'trinket_data.csv')
try:
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        data = [row for row in reader]
except FileNotFoundError:
    print(f"Error: The file 'trinket_data.csv' was not found in the current directory ({current_directory}).")
    input("Press Enter to close the program...")
    sys.exit(1)

# Group data by quality
grouped_data = defaultdict(list)
for row in data:
    grouped_data[row['quality'].lower()].append(row)

# Generate a separate table for each quality
for quality, items in grouped_data.items():
    quality_title = f"List of {quality.capitalize()} Trinkets"

    table_output = f"{{| class=\"wikitable\" style=\"border-collapse:collapse;\"\n"
    table_output += f"! colspan=\"7\" | {quality_title}\n"  # Merged header row
    table_output += "|-\n"  # Header row separator

    # Add column headers
    headers = ["Icon", "Name", "Base Description", "Attuned Description", "Price", "Set Item", "Item Set Name"]
    table_output += "! " + " !! ".join([f"'''{header.title()}'''" for header in headers]) + "\n"

    # Add rows for each item
    for index, row in enumerate(items):
        table_output += "|-\n"  # Row separator
        row_style = get_row_style(quality, index)
        name_color = name_colors.get(quality, "black")
        base_desc, attuned_desc = split_description(row['description'], row_style)
        set_item = "" if row['Set Item'].lower() == 'false' else "✔"
        table_output += (
            f"| style=\"text-align:center; padding:{CELL_PADDING};\" | {row['icon']} "
            f"|| style=\"text-align:center; background-color:{row_style}; color:{name_color}; padding:{CELL_PADDING};\" | <span id=\"{row['name'].replace(' ', '_').lower()}\">{row['name']}</span> "
            f"|| style=\"text-align:center; background-color:{row_style}; padding:{CELL_PADDING};\" | {base_desc} "
            f"|| style=\"text-align:center; background-color:{row_style}; padding:{CELL_PADDING};\" | {attuned_desc} "
            f"|| style=\"text-align:center; background-color:{row_style}; padding:{CELL_PADDING};\" | {row['price']} "
            f"|| style=\"text-align:center; background-color:{row_style}; padding:{CELL_PADDING};\" | {set_item} "
            f"|| style=\"background-color:{row_style}; padding:{CELL_PADDING};\" | {row['Item Set Name']}\n"
        )

    # End the table
    table_output += "|}\n"

    # Save each table to a separate file
    table_file_path = os.path.join(current_directory, f"{quality}_trinkets_table.txt")
    with open(table_file_path, 'w', encoding='utf-8') as f:
        f.write(table_output)

    print(f"Table for {quality.capitalize()} saved to {table_file_path}")
