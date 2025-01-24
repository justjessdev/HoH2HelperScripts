import os
import sys
import json
import base64
import subprocess
import importlib.metadata
from pathlib import Path
from tkinter import filedialog
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def install_requirements():
    """Install required packages from requirements.txt"""
    requirements_file = Path(__file__).parent / "requirements.txt"
    if not requirements_file.exists():
        print("requirements.txt not found")
        return
    
    # Read requirements
    with open(requirements_file) as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    # Check which packages need to be installed
    try:
        installed = {dist.metadata['Name'].lower() for dist in importlib.metadata.distributions()}
    except Exception:
        installed = set()  # If we can't get installed packages, assume none are installed
    
    missing = []
    for requirement in requirements:
        pkg_name = requirement.split('==')[0].split('>=')[0].strip().lower()
        if pkg_name not in installed:
            missing.append(requirement)
    
    if missing:
        print("Installing missing packages...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("All requirements installed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"Error installing packages: {e}")
            sys.exit(1)

# Install requirements before importing them
if __name__ == "__main__":
    install_requirements()

import tkinter as tk
from tkinter import ttk, messagebox
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import mwclient
import threading

class WikiUploaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("HoH2 Wiki File Uploader")
        
        # Ensure credentials directory exists
        self.creds_dir = Path(__file__).parent / "credentials"
        self.creds_dir.mkdir(exist_ok=True)
        
        # Initialize encryption
        self._init_encryption()
        
        # Initialize instance variables first
        self.files_to_upload_dir = None
        self.site = None
        self.is_uploading = False
        self.is_logged_in = False
        self.should_cancel_upload = False
        self.file_exists_cache = {}  # Add cache for file existence
        
        # Initialize token storage
        self.token_file = self.creds_dir / ".wiki_token"
        self.token_data = self.load_token()
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Left side - Configuration and Progress
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # Site Configuration Frame
        site_frame = ttk.LabelFrame(left_frame, text="Site Configuration", padding="5")
        site_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(site_frame, text="Wiki URL:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.site_url_var = tk.StringVar(value="wiki.heroesofhammerwatch2.com")
        ttk.Entry(site_frame, textvariable=self.site_url_var).grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Configure site_frame grid
        site_frame.columnconfigure(1, weight=1)
        
        # Directory Selection Frame
        dir_frame = ttk.LabelFrame(left_frame, text="Directory Selection", padding="5")
        dir_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.dir_path_var = tk.StringVar()
        ttk.Entry(dir_frame, textvariable=self.dir_path_var, state='readonly').grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(dir_frame, text="Browse", command=self.browse_directory).grid(row=0, column=1, padx=5)
        
        # Configure dir_frame grid
        dir_frame.columnconfigure(0, weight=1)
        
        # Login Frame
        login_frame = ttk.LabelFrame(left_frame, text="Login", padding="5")
        login_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(login_frame, text="Username:").grid(row=0, column=0, sticky=tk.W)
        self.username_var = tk.StringVar()
        ttk.Entry(login_frame, textvariable=self.username_var).grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        ttk.Label(login_frame, text="Password:").grid(row=1, column=0, sticky=tk.W)
        self.password_var = tk.StringVar()
        ttk.Entry(login_frame, textvariable=self.password_var, show="*").grid(row=1, column=1, sticky=(tk.W, tk.E))
        
        # Remember me checkbox
        self.remember_me_var = tk.BooleanVar(value=False)
        self.remember_me_checkbox = ttk.Checkbutton(login_frame, text="Remember Me", variable=self.remember_me_var)
        self.remember_me_checkbox.grid(row=2, column=0, columnspan=2, sticky=tk.W)
        
        # Bottom row of login frame with buttons
        login_buttons_frame = ttk.Frame(login_frame)
        login_buttons_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Delete token button on left
        self.delete_token_button = ttk.Button(login_buttons_frame, text="Delete Login Token", command=self.delete_login_token)
        self.delete_token_button.pack(side=tk.LEFT)
        
        # Login button on right
        self.login_button = ttk.Button(login_buttons_frame, text="Log In", command=self.login)
        self.login_button.pack(side=tk.RIGHT)
        
        # Upload Options Frame
        options_frame = ttk.LabelFrame(left_frame, text="Upload Options", padding="5")
        options_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Existing files options
        ttk.Label(options_frame, text="Existing Files:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.existing_files_var = tk.StringVar(value="skip")
        ttk.Radiobutton(options_frame, text="Skip", variable=self.existing_files_var, value="skip").grid(row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(options_frame, text="Update", variable=self.existing_files_var, value="update").grid(row=0, column=2, sticky=tk.W)
        
        # Unknown files options
        ttk.Label(options_frame, text="Unknown Files:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.unknown_files_var = tk.StringVar(value="skip")
        ttk.Radiobutton(options_frame, text="Skip", variable=self.unknown_files_var, value="skip").grid(row=1, column=1, sticky=tk.W)
        ttk.Radiobutton(options_frame, text="Upload", variable=self.unknown_files_var, value="upload").grid(row=1, column=2, sticky=tk.W)
        
        # Description Frame
        desc_frame = ttk.LabelFrame(left_frame, text="Upload Description", padding="5")
        desc_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(desc_frame, text="Additional Description:").grid(row=0, column=0, sticky=tk.W)
        self.desc_var = tk.StringVar()
        ttk.Entry(desc_frame, textvariable=self.desc_var).grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        ttk.Label(desc_frame, text="(Will be appended to 'Uploading file: [filename]')").grid(row=2, column=0, columnspan=2, sticky=tk.W)
        
        # Progress Frame
        progress_frame = ttk.LabelFrame(left_frame, text="Upload Progress", padding="5")
        progress_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.progress_var = tk.StringVar(value="Please log in to start uploading...")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var, wraplength=350)
        self.progress_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Configure progress frame to expand
        progress_frame.columnconfigure(0, weight=1)
        
        # Right side - File Preview
        preview_frame = ttk.LabelFrame(main_frame, text="Files to Upload", padding="5")
        preview_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
        # Preview list with scrollbar
        preview_list_frame = ttk.Frame(preview_frame)
        preview_list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.preview_list = tk.Text(preview_list_frame, width=40, height=10, wrap=tk.NONE)
        self.preview_list.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        preview_scrollbar = ttk.Scrollbar(preview_list_frame, orient=tk.VERTICAL, command=self.preview_list.yview)
        preview_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.preview_list['yscrollcommand'] = preview_scrollbar.set

        # Add horizontal scrollbar
        preview_hscrollbar = ttk.Scrollbar(preview_list_frame, orient=tk.HORIZONTAL, command=self.preview_list.xview)
        preview_hscrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.preview_list['xscrollcommand'] = preview_hscrollbar.set
        
        # Refresh button for preview
        self.refresh_button = ttk.Button(preview_frame, text="Refresh File List", command=self.refresh_file_list)
        self.refresh_button.grid(row=1, column=0, pady=5)
        
        # File count label
        self.file_count_var = tk.StringVar(value="No files found")
        ttk.Label(preview_frame, textvariable=self.file_count_var).grid(row=2, column=0, pady=5)
        
        # Bottom section - Log and Buttons
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Log Frame
        log_frame = ttk.LabelFrame(bottom_frame, text="Upload Log", padding="5")
        log_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.log_text = tk.Text(log_frame, height=10, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text['yscrollcommand'] = scrollbar.set
        
        # Bottom buttons and signature frame
        final_row_frame = ttk.Frame(bottom_frame)
        final_row_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Signature on the left
        signature_frame = ttk.Frame(final_row_frame)
        signature_frame.pack(side=tk.LEFT, fill=tk.X)
        
        signature_label = ttk.Label(signature_frame, text="Created by ", font=('TkDefaultFont', 8, 'italic'), foreground='gray')
        signature_label.pack(side=tk.LEFT)
        
        def open_twitter(event):
            import webbrowser
            webbrowser.open('https://x.com/JustJessDev')
        
        def open_discord(event):
            import webbrowser
            webbrowser.open('https://discord.gg/hammerwatch')
        
        self.signature_link = ttk.Label(signature_frame, text="Jess", font=('TkDefaultFont', 8, 'italic'), cursor="hand2")
        self.signature_link.pack(side=tk.LEFT)
        self.signature_link.bind("<Button-1>", open_twitter)
        self.signature_link.bind("<Enter>", lambda e: self.signature_link.configure(font=('TkDefaultFont', 8, 'italic', 'underline')))
        self.signature_link.bind("<Leave>", lambda e: self.signature_link.configure(font=('TkDefaultFont', 8, 'italic')))
        
        signature_middle = ttk.Label(signature_frame, text=" / JustJessDev in the ", font=('TkDefaultFont', 8, 'italic'), foreground='gray')
        signature_middle.pack(side=tk.LEFT)
        
        self.discord_link = ttk.Label(signature_frame, text="Hammerwatch Discord", font=('TkDefaultFont', 8, 'italic'), cursor="hand2")
        self.discord_link.pack(side=tk.LEFT)
        self.discord_link.bind("<Button-1>", open_discord)
        self.discord_link.bind("<Enter>", lambda e: self.discord_link.configure(font=('TkDefaultFont', 8, 'italic', 'underline')))
        self.discord_link.bind("<Leave>", lambda e: self.discord_link.configure(font=('TkDefaultFont', 8, 'italic')))
        
        # Upload button on the right
        button_frame = ttk.Frame(final_row_frame)
        button_frame.pack(side=tk.RIGHT)
        
        self.upload_button = ttk.Button(button_frame, text="Start Upload", command=self.start_upload)
        self.upload_button.pack(side=tk.RIGHT, padx=5)
        
        self.cancel_button = ttk.Button(button_frame, text="Cancel Upload", command=self.cancel_upload, state='disabled')
        self.cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # Initialize from saved token if exists
        if self.token_data:
            self.username_var.set(self.token_data.get('username', ''))
            self.remember_me_var.set(True)
            self.try_token_login()
        
        # Configure grid weights for dynamic scaling
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        
        main_frame.grid_rowconfigure(0, weight=3)  # More space for the top section
        main_frame.grid_rowconfigure(1, weight=1)  # Less space for the bottom section
        main_frame.grid_columnconfigure(0, weight=1)  # Equal weight for left side
        main_frame.grid_columnconfigure(1, weight=1)  # Equal weight for right side
        
        left_frame.grid_rowconfigure(5, weight=1)  # Progress frame can expand
        left_frame.grid_columnconfigure(0, weight=1)
        
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)
        
        preview_list_frame.grid_rowconfigure(0, weight=1)
        preview_list_frame.grid_columnconfigure(0, weight=1)
        
        bottom_frame.grid_rowconfigure(0, weight=1)
        bottom_frame.grid_columnconfigure(0, weight=1)
        
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        # Calculate initial window size based on content
        self.root.update_idletasks()
        width = max(800, main_frame.winfo_reqwidth() + 40)
        height = max(600, main_frame.winfo_reqheight() + 40)
        self.root.geometry(f"{width}x{height}")
        
        # Set minimum window size
        self.root.minsize(800, 600)

    def _init_encryption(self):
        """Initialize encryption for token storage"""
        key_file = self.creds_dir / ".wiki_key"
        if not key_file.exists():
            # Generate a new key
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=480000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(os.urandom(32)))
            # Save the key and salt
            with open(key_file, 'wb') as f:
                f.write(salt + key)
        else:
            # Load existing key
            with open(key_file, 'rb') as f:
                data = f.read()
                salt = data[:16]
                key = data[16:]
        
        self.fernet = Fernet(key)

    def set_default_directory(self):
        """Set the default directory to files_to_upload_dir in the script's directory"""
        default_dir = Path(__file__).parent / "files_to_upload_dir"
        # Create the directory if it doesn't exist
        default_dir.mkdir(exist_ok=True)
        
        self.files_to_upload_dir = default_dir
        self.dir_path_var.set(str(default_dir))
        self.refresh_file_list()

    def browse_directory(self):
        """Open directory browser dialog"""
        directory = filedialog.askdirectory(
            title="Select Directory",
            initialdir=self.files_to_upload_dir if self.files_to_upload_dir else "."
        )
        if directory:
            self.files_to_upload_dir = Path(directory)
            self.dir_path_var.set(directory)
            self.refresh_file_list()  # Refresh immediately after selection

    def update_button_states(self):
        """Update button states based on login and upload status"""
        if self.is_logged_in:
            self.login_button.state(['disabled'])
            self.upload_button.state(['!disabled'])
            self.refresh_button.state(['!disabled'])
            self.username_var.set(self.username_var.get())  # Keep the username visible
            for widget in self.root.winfo_children():
                if isinstance(widget, ttk.Entry) and widget.winfo_parent() == self.login_frame.winfo_name():
                    widget.state(['disabled'])
            
            # Handle remember me checkbox after login
            if self.remember_me_var.get() and not self.token_data:
                messagebox.showinfo(
                    "Remember Me",
                    "To save your login token, please relaunch the application and check 'Remember Me' before logging in."
                )
                self.remember_me_var.set(False)
        else:
            self.login_button.state(['!disabled'])
            self.upload_button.state(['disabled'])
            self.refresh_button.state(['!disabled'])
            for widget in self.root.winfo_children():
                if isinstance(widget, ttk.Entry) and widget.winfo_parent() == self.login_frame.winfo_name():
                    widget.state(['!disabled'])
        
        # Update cancel button state
        if self.is_uploading:
            self.upload_button.state(['disabled'])
            self.login_button.state(['disabled'])
            self.refresh_button.state(['disabled'])
            self.cancel_button.state(['!disabled'])  # Enable cancel button during upload
        else:
            self.cancel_button.state(['disabled'])  # Disable cancel button when not uploading

    def load_token(self):
        """Load and decrypt saved login token"""
        try:
            if self.token_file.exists():
                with open(self.token_file, 'rb') as f:
                    encrypted_data = f.read()
                    decrypted_data = self.fernet.decrypt(encrypted_data)
                    return json.loads(decrypted_data)
        except Exception:
            pass
        return None

    def save_token(self, token_data):
        """Encrypt and save login token"""
        try:
            encrypted_data = self.fernet.encrypt(json.dumps(token_data).encode())
            with open(self.token_file, 'wb') as f:
                f.write(encrypted_data)
        except Exception as e:
            self.log_message(f"Failed to save login token: {str(e)}")

    def delete_login_token(self):
        """Delete saved login token"""
        if self.token_file.exists():
            try:
                self.token_file.unlink()
                self.token_data = None
                messagebox.showinfo("Success", "Login token deleted successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete login token: {str(e)}")
        else:
            messagebox.showinfo("Info", "No saved login token found")

    def try_token_login(self):
        """Attempt to login using saved token"""
        if not self.token_data:
            return
        
        try:
            self.site = mwclient.Site(self.site_url_var.get(), path='/')
            self.site.login(username=self.token_data['username'], password=self.token_data['password'])
            self.is_logged_in = True
            self.progress_var.set("Logged in successfully using saved token")
            self.log_message(f"Logged in as {self.token_data['username']} using saved token")
            self.update_button_states()
            self.refresh_file_list()
        except Exception as e:
            self.log_message(f"Failed to login with saved token: {str(e)}")
            self.token_data = None
            if self.token_file.exists():
                self.token_file.unlink()

    def login(self):
        """Handle login process"""
        if not self.username_var.get() or not self.password_var.get():
            messagebox.showerror("Error", "Please enter both username and password")
            return
        
        self.progress_var.set("Logging in...")
        self.login_button.state(['disabled'])
        
        # Run login in a separate thread
        threading.Thread(target=self._login_process, daemon=True).start()

    def _login_process(self):
        """Internal method to handle the login process in a separate thread"""
        try:
            if self.connect_to_wiki():
                self.is_logged_in = True
                self.progress_var.set("Logged in successfully. Checking file statuses...")
                self.log_message(f"Logged in as {self.username_var.get()}")
                
                # Handle remember me
                if self.remember_me_var.get():
                    # Save new token
                    self.token_data = {
                        'username': self.username_var.get(),
                        'password': self.password_var.get()
                    }
                    self.save_token(self.token_data)
                
                # Refresh file list to check existence status
                self.refresh_file_list()
                self.progress_var.set("Ready to upload...")
            else:
                self.is_logged_in = False
                self.progress_var.set("Login failed. Please try again.")
        except Exception as e:
            self.is_logged_in = False
            self.log_message(f"Login error: {str(e)}")
            self.progress_var.set("Login failed. Please try again.")
        finally:
            self.root.after(0, self.update_button_states)

    def connect_to_wiki(self):
        try:
            # Create session with retry strategy
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[500, 502, 503, 504]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            # Connect to the wiki using the configured URL
            self.site = mwclient.Site(self.site_url_var.get(), path='/', clients_useragent='HoH2WikiUploader/1.0')
            self.site.login(username=self.username_var.get(), password=self.password_var.get())
            return True
        except Exception as e:
            messagebox.showerror("Login Error", f"Failed to connect to the wiki: {str(e)}")
            return False

    def upload_file(self, file_path):
        """Upload a single file to the wiki"""
        try:
            filename = file_path.name
            
            # Check if file already exists
            existing_file = self.site.images[filename]
            if existing_file.exists:
                if self.existing_files_var.get() == "skip":
                    self.log_message(f"Skipped {filename} (already exists)")
                    return False
                elif self.existing_files_var.get() == "update":
                    # File will be overwritten, handled by ignore=True in upload
                    pass
            elif not existing_file.exists and self.unknown_files_var.get() == "skip":
                self.log_message(f"Skipped {filename} (unknown status)")
                return False
            
            # Create description with optional additional text
            description = f"Uploading file: {filename[:-4]}"
            if self.desc_var.get().strip():
                description += f" - {self.desc_var.get().strip()}"
            
            with open(file_path, 'rb') as f:
                self.site.upload(f, filename, description=description, ignore=self.existing_files_var.get() == "update")
            self.log_message(f"Successfully uploaded {filename}")
            return True
        except Exception as e:
            self.log_message(f"Error uploading {filename}: {str(e)}")
            return False

    def start_upload(self):
        if not self.is_logged_in:
            messagebox.showerror("Error", "Please log in first")
            return
        
        if self.is_uploading:
            return
        
        # If update mode is selected and we have existing files in our list, warn user
        if self.existing_files_var.get() == "update":
            # Check if we have any files marked as [EXISTS] in our preview list
            preview_content = self.preview_list.get('1.0', tk.END)
            if '[EXISTS]' in preview_content:
                warning_message = (
                    "You have selected to overwrite existing files on the wiki.\n\n"
                    "This action cannot be undone through the application.\n\n"
                    "To reverse this action, you must manually revert the changes to the uploaded files from the wiki.\n\n"
                    "Are you sure you want to proceed?"
                )
                
                if not messagebox.askyesno(
                    "Warning - Files Will Be Overwritten",
                    warning_message,
                    icon='warning'
                ):
                    return
        
        self.is_uploading = True
        self.should_cancel_upload = False  # Reset cancel flag
        self.update_button_states()
        threading.Thread(target=self.upload_process, daemon=True).start()

    def upload_process(self):
        """Process all files in the selected directory"""
        try:
            if not self.files_to_upload_dir or not self.files_to_upload_dir.exists():
                self.progress_var.set("No directory selected")
                messagebox.showinfo("Upload Complete", "No directory selected.")
                return
            
            # Get all files (excluding directories)
            wiki_files = sorted(path for path in self.files_to_upload_dir.rglob('*') if path.is_file())
            total_files = len(wiki_files)
            
            if total_files == 0:
                self.progress_var.set("No files to upload")
                messagebox.showinfo("Upload Complete", "No files found to upload.")
                return
            
            self.progress_bar['maximum'] = total_files
            successful_uploads = 0
            skipped_files = 0
            
            for i, file_path in enumerate(wiki_files, 1):
                if self.should_cancel_upload:
                    self.progress_var.set("Upload cancelled")
                    messagebox.showinfo(
                        "Upload Cancelled",
                        f"Upload process cancelled. {successful_uploads} files uploaded, {skipped_files} files skipped."
                    )
                    break
                
                self.progress_bar['value'] = i
                rel_path = file_path.relative_to(self.files_to_upload_dir)
                self.progress_var.set(f"Uploading {rel_path} ({i}/{total_files})")
                
                result = self.upload_file(file_path)
                if result is None:  # User cancelled
                    self.progress_var.set("Upload cancelled")
                    messagebox.showinfo(
                        "Upload Cancelled",
                        f"Upload process cancelled. {successful_uploads} files uploaded, {skipped_files} files skipped."
                    )
                    break
                elif result:  # Successful upload
                    successful_uploads += 1
                else:  # Failed or skipped
                    skipped_files += 1
                
                self.root.update_idletasks()
            
            if not self.should_cancel_upload:
                self.progress_var.set(
                    f"Upload complete. {successful_uploads}/{total_files} files uploaded successfully. "
                    f"{skipped_files} files skipped."
                )
                messagebox.showinfo(
                    "Upload Complete",
                    f"Successfully uploaded {successful_uploads} out of {total_files} files.\n"
                    f"{skipped_files} files were skipped."
                )
            
        except Exception as e:
            self.log_message(f"Error during upload process: {str(e)}")
            messagebox.showerror("Error", f"An error occurred during the upload process: {str(e)}")
        finally:
            self.progress_bar['value'] = 0
            self.is_uploading = False
            self.should_cancel_upload = False
            self.update_button_states()

    def check_files_exist_on_wiki(self, filenames):
        """Batch check if multiple files exist on the wiki"""
        if not self.is_logged_in or not self.site:
            return {filename: None for filename in filenames}
        
        try:
            # First check cache
            results = {filename: self.file_exists_cache.get(filename) for filename in filenames}
            
            # Filter out filenames that need to be checked
            to_check = [f for f in filenames if results[f] is None]
            
            if to_check:
                # Use allimages query to get all files in one API call
                # Break into chunks of 50 to avoid too large requests
                chunk_size = 50
                for i in range(0, len(to_check), chunk_size):
                    chunk = to_check[i:i + chunk_size]
                    
                    try:
                        # First try to get the files directly
                        for filename in chunk:
                            try:
                                file_info = self.site.images[filename]
                                exists = file_info.exists
                                results[filename] = exists
                                self.file_exists_cache[filename] = exists
                            except Exception as e:
                                self.log_message(f"Error checking individual file {filename}: {str(e)}")
                                results[filename] = None
                    
                    except Exception as e:
                        self.log_message(f"Error checking chunk {i//chunk_size + 1}: {str(e)}")
                        # On chunk error, mark those files as unknown
                        for filename in chunk:
                            if filename not in results:
                                results[filename] = None
            
            return results
            
        except Exception as e:
            self.log_message(f"Error in check_files_exist_on_wiki: {str(e)}")
            # On error, return None for uncached results
            return {filename: self.file_exists_cache.get(filename) for filename in filenames}

    def refresh_file_list(self):
        """Update the preview list with current files in the selected directory"""
        self.preview_list.config(state='normal')  # Enable editing temporarily
        self.preview_list.delete('1.0', tk.END)
        
        if not self.files_to_upload_dir or not self.files_to_upload_dir.exists():
            self.file_count_var.set("No directory selected")
            self.preview_list.insert(tk.END, "Please select a directory\n")
            self.preview_list.config(state='disabled')
            return
        
        # Start the background refresh process
        self.preview_list.insert(tk.END, "Checking file statuses...\n")
        threading.Thread(target=self._refresh_file_list_process, daemon=True).start()

    def _refresh_file_list_process(self):
        """Background process for refreshing file list"""
        try:
            # Get all files (excluding directories)
            wiki_files = sorted(path for path in self.files_to_upload_dir.rglob('*') if path.is_file())
            total_files = len(wiki_files)
            
            # Count file types and check existence
            file_types = {}
            existing_count = 0
            new_count = 0
            unknown_count = 0
            
            # Prepare the new content
            content = []
            
            # Set up progress tracking for existence checking
            if self.is_logged_in and total_files > 0:
                self.root.after(0, lambda: setattr(self.progress_bar, 'maximum', total_files))
                self.root.after(0, lambda: setattr(self.progress_bar, 'value', 0))
            
            # Get the width of the progress label (approximate characters)
            progress_width = 60
            
            # Process files in chunks for batch existence checking
            chunk_size = 50
            for i in range(0, len(wiki_files), chunk_size):
                chunk = wiki_files[i:i + chunk_size]
                
                # Update progress for this chunk
                progress_text = f"Checking file status: Batch {i//chunk_size + 1}/{(total_files + chunk_size - 1)//chunk_size}"
                self.root.after(0, lambda text=progress_text: self.progress_var.set(text))
                self.root.after(0, lambda val=i: setattr(self.progress_bar, 'value', val))
                
                # Batch check existence
                filenames = [f.name for f in chunk]
                existence_results = self.check_files_exist_on_wiki(filenames) if self.is_logged_in else {f: None for f in filenames}
                
                # Process results for this chunk
                for file_path in chunk:
                    ext = file_path.suffix.lower() or '(no extension)'
                    file_types[ext] = file_types.get(ext, 0) + 1
                    
                    rel_path = file_path.relative_to(self.files_to_upload_dir)
                    exists = existence_results.get(file_path.name)
                    
                    if exists is None:
                        status = "[?]"
                        tag = 'unknown'
                        unknown_count += 1
                    elif exists:
                        status = "[EXISTS]"
                        tag = 'existing'
                        existing_count += 1
                    else:
                        status = "[NEW]"
                        tag = 'new'
                        new_count += 1
                    
                    content.append((f"{status} {rel_path}\n", tag))
            
            # Update UI in the main thread
            def update_ui():
                self.preview_list.config(state='normal')
                self.preview_list.delete('1.0', tk.END)
                
                # Configure tag colors
                self.preview_list.tag_configure('existing', foreground='orange')
                self.preview_list.tag_configure('new', foreground='green')
                self.preview_list.tag_configure('unknown', foreground='gray')
                
                # Insert content with tags
                for text, tag in content:
                    self.preview_list.insert(tk.END, text, tag)
                
                # Create file count message
                type_counts = [f"{count} {ext}" for ext, count in sorted(file_types.items())]
                count_msg = f"Found {total_files} file{'s' if total_files != 1 else ''}\n"
                count_msg += "Types: " + ", ".join(type_counts) + "\n"
                if self.is_logged_in:
                    count_msg += f"Status: {new_count} new, {existing_count} existing"
                    if unknown_count > 0:
                        count_msg += f", {unknown_count} unknown"
                
                self.file_count_var.set(count_msg)
                self.progress_bar['value'] = 0
                self.progress_var.set("File status check complete")
                
                if total_files == 0:
                    self.preview_list.insert(tk.END, "No files found in selected directory\n")
                    self.preview_list.config(state='disabled')
                else:
                    self.preview_list.config(state='disabled')  # Make read-only
            
            self.root.after(0, update_ui)
            
        except Exception as e:
            def show_error():
                self.log_message(f"Error refreshing file list: {str(e)}")
                messagebox.showerror("Error", f"An error occurred while refreshing the file list: {str(e)}")
            self.root.after(0, show_error)

    def log_message(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def cancel_upload(self):
        """Cancel the current upload process"""
        self.should_cancel_upload = True
        self.progress_var.set("Canceling upload...")
        self.cancel_button.state(['disabled'])

def main():
    root = tk.Tk()
    app = WikiUploaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 