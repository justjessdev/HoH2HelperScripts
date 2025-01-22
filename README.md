# HoH2HelperScripts
Scripts designed to assist in extracting data from Heroes of Hammerwatch II game files and formatting it for use in maintaining the game's wiki.

Wiki: https://wiki.heroesofhammerwatch2.com/index.php/Main_Page

Heroes of Hammerwatch II is developed by Crackshell: https://www.crackshell.dk/

# Trinket Data Extractor

![gif of the trinket scripts working](https://github.com/justjessdev/HoH2HelperScripts/blob/main/images/trinket_data_extractor.gif)

## Description
This script is designed to parse `.sval` files, which are structured data files, and generate human-readable CSV files, which can then also be used in the automatic generation of MediaWiki formatted tables.

The script processes item and set data contained in the `.sval` files and outputs two CSV files:

1. **`trinket_data.csv`:**
	- Contains  information about individual trinkets found in the `.sval` files.
	- Combines `desc` (base trinket/item description) and `attune-desc` (attuned description) into a single `description` column, formatted with `Base:` and `Attuned:` labels.
		- **ToDo: I want to move this to the Wiki Formatter so that the raw data from this script can be used for more general purposes.**
	- Excludes certain unused or irrelevant fields such as `id` and `skill`.
		- **ToDo: I want to move this to the Wiki Formatter so that the raw data from this script can be used for more general purposes.**
	- Includes metadata such as `Set Item` (a boolean indicating if the item belongs to a set) and `Item Set Name` (the name of the set the item belongs to).

2. **`trinket_sets_data.csv`:**
	- Contains information about item sets parsed from the `sets.sval` file.
	- Lists the set name, total items in the set, the names of items in the set (one per line), and the effects of the set formatted by tier.

## Features
- **Dynamic Item Parsing:** Automatically reads all `.sval` files in the directory to retrieve item information, and will ideally continue to work as new items are added and values are tuned.
- **Set Matching:** Correlates item IDs from the `sets.sval` file with their respective names from other `.sval` files.
- **Flexible Formatting:** Ensures multi-line descriptions (`\n`) in `desc` and `attune-desc` fields are properly formatted in the CSV.

## Usage
1. Navigate to your Heroes of Hammerwatch II install directory.
	- `\steamapps\common\Heroes of Hammerwatch 2`
2. Run `PACKAGER.exe`
3. In the top-left, select `Extract base resources` (the yellow box icon).
	- Once complete, you will have a directory named after the build ID containing the game's assets in that version.
	- ie: `unpacked_assets_118`
4. In this directory, navigate to the `trinkets` data.
	- ie: `\unpacked_assets_118\tweak\trinkets`
5. Place the scripts in the directory containing the `.sval` files of each quality (ie: `common.sval`, `uncommon.sval`, etc) and the `sets.sval` file.
6. Run the script using Python:
	```bash
	python trinket_data_extractor.py
	```
7. After execution, two CSV files will be generated in the same directory:
	- `trinket_data.csv`
	- `trinket_sets_data.csv`

## Requirements
- Python 3.6 or later

## Notes
- The script automatically detects all `.sval` files in the directory where it is run. If there's extra stuff in there that isn't trinket data, it will pick it up and likely malform the output data.
- Ensure the `sets.sval` file exists in the same directory if you want set-related data to be included in the output.

## Example
### `trinket_data.csv`
| Icon   | Name            | Description                      | Price | Quality | Set Item | Item Set Name |
|--------|-----------------|----------------------------------|-------|---------|----------|---------------|
| icon1  | Fire Gemstone   | Base: Increases fire damage.\nAttuned: Provides fire immunity. | 100   | Rare    | TRUE     | Infused Gems  |
| icon2  | Ice Gemstone    | Base: Increases ice damage.\nAttuned: Provides ice immunity.  | 100   | Rare    | TRUE     | Infused Gems  |

### `trinket_sets_data.csv`
| Item Set Name | Items in Set | Set Items             | Set Effect                  |
|---------------|--------------|-----------------------|-----------------------------|
| Infused Gems  | 4            | Fire Gemstone\nIce Gemstone\nLightning Gemstone\nPoison Gemstone | 2: +5% Damage\n\n4: +20% Resistances |


# Trinket Wiki Formatter

## Description

This script processes the output data from the Trinket Data Extractor (`trinket_data.csv`, `trinket_sets_data.csv`) and generates MediaWiki-formatted tables for each unique trinket quality (e.g., Common, Rare, Epic).

The script outputs each table into a separate file named after the quality, making it easier to integrate into the wiki.

## Features
- Processes `trinket_data.csv` and `trinket_sets_data.csv` files located in the same directory as the script.
- Groups trinkets by their `Quality` value (e.g., Common, Rare, Epic).
- Generates MediaWiki tables with the following columns:
	- **Icon**: Displays the trinket's icon. (**ToDo: HAVE NOT AUTOMATED THIS YET**)
	- **Name**: Colored based on the trinket's quality.
	- **Description**: Formats multiline descriptions, distinguishing `Base:` and `Attuned:` sections.
	- **Price**: Displays the trinket's base price.
	- **Quality**: Colored label for the quality.
	- **Set Item**: Indicates whether the trinket is part of a set (✔ or ✘).
	- **Item Set Name**: Displays the name of the item set that the trinket is a part of.
- Saves each table in a separate `.txt` file (ie: `common_trinkets_table.txt`).

## Usage

1. **Prepare the .csv Files:**
	- Follow the steps for the **Trinket Data Extractor** to get your data.
	- Ensure the input file is named `trinket_data.csv`.
	- Place this script in the directory with your `trinket_data.csv` and `trinket_sets_data.csv`.
	- The csv should have the following columns:
		- `icon`: Path or representation of the trinket's icon.
		- `name`: Name of the trinket.
		- `description`: Multiline description of the trinket, optionally containing `Base:` and `Attuned:` prefixes.
		- `price`: Price of the trinket.
		- `quality`: Quality of the trinket (e.g., Common, Rare, Epic).
		- `Set Item`: Boolean value (`true` or `false`) indicating if it's part of a set.
		- `Item Set Name`: Name of the associated item set.

2. **Run the Script:**
	- Run the script using Python:
	```bash
	python trinket_data_extractor.py
	```
	- The script will read the `trinket_data.csv` and `trinket_sets_data.csv` file, process the data, and generate the output tables.

3. **Output Files:**
	- For each unique quality (e.g., Common, Rare), a `.txt` file will be created in the same directory.
	- File names will follow the pattern: `<quality>_trinkets_table.txt` (e.g., `common_trinkets_table.txt`).

4. **Integrate into Your Wiki:**
	- Copy the content of each `.txt` file into the corresponding MediaWiki template page.
	- ie: https://wiki.heroesofhammerwatch2.com/index.php/Template:TrinketsCommon

## Notes
n/a

### Color Customizations
The following quality colors are used:
- **Common**: `#72777d`
- **Uncommon**: `#00dc00`
- **Rare**: `#33ccff`
- **Epic**: `#c975fc`
- **Cursed**: `Red`

You can customize these colors by modifying the `color_quality` function in the script.

### Description Formatting
- Descriptions with only `Base:` are cleaned to remove the prefix.
- Newlines in descriptions are replaced with `<br>` for proper formatting in MediaWiki.

## Requirements
- Python 3.6 or higher.

## Example
**Input CSV:**
```csv
icon,name,description,price,quality,Set Item,Item Set Name
icon_path,Amulet of Health,"Base: +30 Health\nAttuned: +60 Health",200,Common,true,Amulets of Life
```

**Generated Table (common_trinkets_table.txt):**
```mediawiki
{| class="wikitable"
! colspan="7" | List of Common Trinkets
|-
! Icon !! Name !! Description !! Price !! Quality !! Set Item !! Item Set Name
|-
| style="text-align:center;" | icon_path || style="color:#72777d;" | <span id="amulet_of_health">Amulet of Health</span> || style="text-align:left;" | '''Base:''' +30 Health<br>'''Attuned:''' +60 Health || style="text-align:center;" | 200 || style="text-align:center;" | <span style="color:#72777d;">Common</span> || style="text-align:center;" | ✔ || Amulets of Life
|}
```
