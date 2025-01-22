import os
import csv
from collections import defaultdict

# Load the data from the current directory
current_directory = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_directory, 'trinket_data.csv')
try:
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        data = [row for row in reader]
except FileNotFoundError:
    print(f"Error: The file 'output.csv' was not found in the current directory ({current_directory}).")
    input("Press Enter to close the program...")
    sys.exit(1)

# Helper function to apply color coding to Quality column
def color_quality(quality):
    colors = {
        "common": "#9ca0a6",
        "uncommon": "#00dc00",
        "rare": "#33ccff",
        "epic": "#c975fc",
        "cursed": "Red"
    }
    return colors.get(quality, "Black")

# Helper function to replace True/False with corresponding symbols, mirroring HoH1 formatting
def format_boolean(value):
    return "✔" if value.lower() == 'true' else "✘"

# Escape pipes and handle newlines in the description to prevent breaking cells
def format_description(description):
    description = description.replace('|', '&#124;')
    description = description.replace('\n', '<br>')  # Replace newlines with HTML line breaks
    if "Base:" in description and "Attuned:" not in description:
        description = description.replace("Base:", "").strip()  # Remove "Base:" if it's the only prefix (will eventually make it so this script handles merging the "Base:" and "Attuned:" description data)
    description = description.replace("Base:", "'''Base:'''")  # I don't like that I did it this way but here we are
    description = description.replace("Attuned:", "'''Attuned:'''")  # re: ↑
    return description

# Group data by quality
grouped_data = defaultdict(list)
for row in data:
    grouped_data[row['quality'].lower()].append(row)

# Generate a separate table for each quality
for quality, items in grouped_data.items():
    quality_title = f"List of {quality.capitalize()} Trinkets"
    quality_color = color_quality(quality)

    table_output = f"{{| class=\"wikitable\"\n"
    table_output += f"! colspan=\"7\" | {quality_title}\n"  # Merged header row
    table_output += "|-\n"  # Header row separator

    # Add column headers with formatting
    headers = ["Icon", "Name", "Description", "Price", "Quality", "Set Item", "Item Set Name"]
    table_output += "! " + " !! ".join([f"'''{header.title()}'''" for header in headers]) + "\n"

    # Add the data rows
    for row in items:
        table_output += "|-\n"  # Row separator
        description = format_description(row['description'])  # ToDo: Move formatting of base and attuned item description data to this part of the script, remove from data extractor
        set_item = format_boolean(row['Set Item'])
        table_output += f"| style=\"text-align:center;\" | {row['icon']} || style=\"color:{quality_color};\" | <span id=\"{row['name'].replace(' ', '_').lower()}\">{row['name']}</span> || style=\"text-align:left;\" | {description} || style=\"text-align:center;\" | {row['price']} || style=\"text-align:center;\" | <span style=\"color:{quality_color};\">{quality.capitalize()}</span> || style=\"text-align:center;\" | {set_item} || {row['Item Set Name']}\n"

    # End the table
    table_output += "|}\n"

    # Save each table to a separate file
    table_file_path = os.path.join(current_directory, f"{quality}_trinkets_table.txt")
    with open(table_file_path, 'w', encoding='utf-8') as f:
        f.write(table_output)

    print(f"Table for {quality.capitalize()} saved to {table_file_path}")

# Pause before closing
# input("Press Enter to close the program...")
