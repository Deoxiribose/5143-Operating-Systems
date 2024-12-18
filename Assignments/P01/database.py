import sqlite3
import getpass
import datetime
import readline
import os

import sqlite3
# Connect to the SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('filesystem.db')
cursor = conn.cursor()

# Create users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL  -- In production, passwords should be hashed!
)
''')

# Create filesystem table with permissions and ownership
cursor.execute('''
CREATE TABLE IF NOT EXISTS filesystem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT CHECK(type IN ('file', 'directory')) NOT NULL,
    content TEXT,
    parent_id INTEGER,
    owner_id INTEGER,
    permissions TEXT DEFAULT 'rwxr-xr-x',
    FOREIGN KEY (parent_id) REFERENCES filesystem(id),
    FOREIGN KEY (owner_id) REFERENCES users(id),
    UNIQUE(name, parent_id, type)
)
''')

# Create root user if it doesn't exist
cursor.execute("SELECT * FROM users WHERE id = 1")
if not cursor.fetchone():
    cursor.execute('''
    INSERT INTO users (id, username, password)
    VALUES (1, 'root', 'rootpassword')
    ''')
    conn.commit()

# Create the root directory if it doesn't exist
cursor.execute("SELECT * FROM filesystem WHERE id = 1")
if not cursor.fetchone():
    cursor.execute('''
    INSERT INTO filesystem (id, name, type, parent_id, owner_id)
    VALUES (1, '/', 'directory', NULL, 1)
    ''')
    conn.commit()
    
# Check if 'size' and 'modification_date' columns exist, and add them if they don't
cursor.execute("PRAGMA table_info(filesystem)")
columns = [column[1] for column in cursor.fetchall()]
if 'size' not in columns:
    cursor.execute('ALTER TABLE filesystem ADD COLUMN size INTEGER DEFAULT 0')
    print("Column 'size' added to 'filesystem' table.")
else:
    print("filesystem operational\n")
if 'modification_date' not in columns:
    cursor.execute('ALTER TABLE filesystem ADD COLUMN modification_date TEXT DEFAULT ""')
    print("Column 'modification_date' added to 'filesystem' table.")
else:
    print("...")
conn.commit()

#Commands for auto suggest
COMMANDS = [
    'exit', 'register', 'login', 'logout', 'pwd', 'ls', 'cd',
    'mkdir', 'rmdir', 'touch', 'cat', 'echo', 'cp', 'mv', 'rm',
    'chmod', 'head', 'tail', 'grep', 'wc', 'write'
]

HISTORY_FILE = os.path.expanduser('~/.my_shell_history')

#Auto suggestions
def completer(text, state):
    buffer = readline.get_line_buffer()
    line = buffer.lstrip()
    stripped_line = buffer.rstrip()
    split_line = stripped_line.split()
    
    # Determine if we're completing a command or an argument
    if len(split_line) == 0 or (len(split_line) == 1 and buffer.endswith(' ')):
        # Completing a command
        options = [cmd for cmd in COMMANDS if cmd.startswith(text)]
    else:
        # Completing a filename or directory
        # Get the current directory contents
        options = get_current_directory_contents()
        options = [name for name in options if name.startswith(text)]
    
    if state < len(options):
        return options[state] + ' '
    else:
        return None

readline.set_completer(completer)
readline.parse_and_bind('tab: complete')

def load_history():
    if os.path.exists(HISTORY_FILE):
        readline.read_history_file(HISTORY_FILE)

def save_history():
    readline.write_history_file(HISTORY_FILE)



# Initialize global variables
current_user = None
current_directory_id = 1  # Will be set to home directory upon login

#First Iteration of Current Dir. for auto suggest.
def get_current_directory_contents():
    global current_directory_id
    cursor.execute('''
    SELECT name FROM filesystem
    WHERE parent_id = ?
    ''', (current_directory_id,))
    items = cursor.fetchall()
    return [item[0] for item in items]

# Helper function to get the current directory path
def get_current_directory_path():
    path = ''
    dir_id = current_directory_id
    while dir_id != 1:
        cursor.execute('SELECT name, parent_id FROM filesystem WHERE id = ?', (dir_id,))
        result = cursor.fetchone()
        if result:
            name, parent_id = result
            #Mess with path format
            path = '/' + name + path
            dir_id = parent_id
        else:
            break
    return '/' if not path else path

# User authentication functions
def register(username, password):
    username = username.lower()
    try:
        cursor.execute('''
        INSERT INTO users (username, password)
        VALUES (?, ?)
        ''', (username, password))
        conn.commit()
        print(f"User '{username}' registered successfully.")
        # Create home directory
        user_home_dir = f"/home/{username}"
        mkdir_p(user_home_dir, owner_username=username)
    except sqlite3.IntegrityError:
        print("Error: Username already exists.")

def login(username, password):
    global current_user, current_directory_id
    username = username.lower()
    cursor.execute('''
    SELECT id, username FROM users
    WHERE username = ? AND password = ?
    ''', (username, password))
    user = cursor.fetchone()
    if user:
        current_user = {'id': user[0], 'username': user[1]}
        print(f"User '{username}' logged in.")
        # Set current directory to user's home directory
        user_home_dir = f"/home/{username}"
        home_dir_id = get_directory_id_by_path(user_home_dir)
        if home_dir_id:
            current_directory_id = home_dir_id
        else:
            # Home directory doesn't exist, create it
            mkdir_p(user_home_dir, owner_username=username)
            current_directory_id = get_directory_id_by_path(user_home_dir)
    else:
        print("Invalid username or password.")
        
def mkdir(directory_name):
    global current_user, current_directory_id
    if not current_user:
        print("No user logged in.")
        return
    if not has_permission(current_directory_id, 'write') or not has_permission(current_directory_id, 'execute'):
        print("Permission denied.")
        return
    # Check if the directory already exists
    cursor.execute('''
    SELECT id FROM filesystem
    WHERE name = ? AND type = 'directory' AND parent_id = ?
    ''', (directory_name, current_directory_id))
    if cursor.fetchone():
        print(f"Error: Directory '{directory_name}' already exists.")
        return
    try:
        now = datetime.datetime.now().isoformat()
        cursor.execute('''
        INSERT INTO filesystem (name, type, parent_id, owner_id, size, modification_date)
        VALUES (?, 'directory', ?, ?, ?, ?)
        ''', (directory_name, current_directory_id, current_user['id'], 0, now))
        conn.commit()
        print(f"Directory '{directory_name}' created.")
    except sqlite3.IntegrityError as e:
        print(f"Error: {e}")


def logout():
    global current_user
    if current_user:
        print(f"User '{current_user['username']}' logged out.")
        current_user = None
    else:
        print("No user is currently logged in.")

# Function to create directories along a given path
def mkdir_p(path, owner_username=None):
    global current_directory_id
    if not owner_username:
        if not current_user:
            print("No user logged in.")
            return
        owner_id = current_user['id']
    else:
        cursor.execute('SELECT id FROM users WHERE username = ?', (owner_username.lower(),))
        owner = cursor.fetchone()
        if owner:
            owner_id = owner[0]
        else:
            print(f"User '{owner_username}' does not exist.")
            return

    # Split the path and iterate through each part
    parts = [p for p in path.strip('/').split('/') if p]
    dir_id = 1  # Start from the root directory with ID 1
    for part in parts:
        cursor.execute('''
        SELECT id FROM filesystem
        WHERE name = ? AND type = 'directory' AND parent_id = ?
        ''', (part, dir_id))
        result = cursor.fetchone()
        if result:
            dir_id = result[0]  # Directory already exists, move into it
        else:
            # Create the directory
            cursor.execute('''
            INSERT INTO filesystem (name, type, parent_id, owner_id, permissions)
            VALUES (?, 'directory', ?, ?, 'rwxr-xr-x')
            ''', (part, dir_id, owner_id))
            conn.commit()
            dir_id = cursor.lastrowid


# Function to get directory ID by path
def get_directory_id_by_path(path):
    parts = [p for p in path.strip('/').split('/') if p]
    dir_id = 1  # Start from root
    for part in parts:
        cursor.execute('''
        SELECT id FROM filesystem
        WHERE name = ? AND type = 'directory' AND parent_id = ?
        ''', (part, dir_id))
        result = cursor.fetchone()
        if result:
            dir_id = result[0]
        else:
            return None
    return dir_id

# Permission checking function
def has_permission(item_id, permission_type):
    if not current_user:
        print("No user logged in.")
        return False

    cursor.execute('''
    SELECT permissions, owner_id FROM filesystem
    WHERE id = ?
    ''', (item_id,))
    result = cursor.fetchone()
    if not result:
        print("Item does not exist.")
        return False
    permissions, owner_id = result

    perm_indices = {'read': 0, 'write': 1, 'execute': 2}
    perm_index = perm_indices[permission_type]

    # Owner permissions
    if current_user['id'] == owner_id:
        perm = permissions[perm_index]
    else:
        # Others permissions
        perm = permissions[6 + perm_index]
    return perm != '-'

#Helper Function for Sizing Format. 
def format_size(size):
    # Human-readable format
    for unit in ['B', 'K', 'M', 'G', 'T']:
        if size < 1024:
            return f"{size}{unit}"
        size /= 1024
    return f"{size}P"