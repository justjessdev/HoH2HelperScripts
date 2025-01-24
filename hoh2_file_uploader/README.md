# HoH2 Wiki File Uploader

A simple GUI application for uploading files to the Heroes of Hammerwatch 2 Wiki. (theoretically works for any mediawiki based wiki)

## Requirements

- Python 3.8 or higher (download from [python.org](https://www.python.org/downloads/))
- Required Python packages (automatically installed when running the application)
  - mwclient
  - requests
  - urllib3

## Installation

1. Download and install Python from [python.org](https://www.python.org/downloads/)
   - During installation, make sure to check "Add Python to PATH"
   - Minimum supported version is Python 3.8

2. Download or clone this repository

## Running the Application

1. Open a terminal/command prompt
2. Navigate to the directory containing `hoh2_wiki_file_uploader.py`
3. Run the application:
   ```
   python hoh2_wiki_file_uploader.py
   ```
   - The application will automatically install required dependencies on first run
   - A directory named `files_to_upload_dir` will be created in the same location as the script

## Usage

1. Log in with your wiki credentials
   - Check "Remember Me" to save your login token for future sessions
2. Select a directory containing files to upload
   - Files will be shown with their status, ie: whether or not they exist on the wiki (New/Exists/Unknown)
3. Configure upload options:
   - Existing Files: Choose to skip or update files that already exist on the wiki
   - Unknown Files: Choose to skip or attempt upload for files with unknown status
4. Click "Start Upload" to begin the upload process
   - You can cancel the upload at any time using the "Cancel Upload" button
