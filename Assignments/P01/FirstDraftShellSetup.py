import sqlite3
import getpass
import datetime
import re
import readline
import os

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

# Filesystem command implementations
def ls(options=[]):
    if not has_permission(current_directory_id, 'execute'):
        print("Permission denied.")
        return
    
    show_all = False
    long_format = False
    human_readable = False
    
    # Parse options
    for option in options:
        if option == '-a':
            show_all = True
        elif option == '-l':
            long_format = True
        elif option == '-h':
            human_readable = True
        else:
            print(f"Unknown option: {option}")
            return
    
    # Fetch directory contents
    cursor.execute('''
    SELECT name, type, permissions, owner_id, size, modification_date FROM filesystem
    WHERE parent_id = ?
    ''', (current_directory_id,))
    items = cursor.fetchall()
    
    if not items:
        print("Directory is empty.")
    else:
        for item in items:
            name, item_type, permissions, owner_id, size, modification_date = item
            # Skip hidden files if '-a' not specified
            if not show_all and name.startswith('.'):
                continue
            if long_format:
                # Fetch owner's username
                cursor.execute('SELECT username FROM users WHERE id = ?', (owner_id,))
                owner_name = cursor.fetchone()[0]
                # Format size
                display_size = size
                if human_readable:
                    display_size = format_size(size)
                # Format date
                date_str = modification_date.split('T')[0] if modification_date else ''
                print(f"{permissions} {owner_name} {display_size} {date_str} {item_type}: {name}")
            else:
                print(f"{item_type}: {name}")

def cd(directory_name=None):
    global current_directory_id

    if directory_name is None or directory_name.strip() == '':
        # Change to the user's home directory
        if current_user:
            user_home_dir = f"/home/{current_user['username']}"
            home_dir_id = get_directory_id_by_path(user_home_dir)
            if home_dir_id:
                current_directory_id = home_dir_id
                return
            else:
                print("Home directory not found.")
                return
        else:
            print("No user is currently logged in.")
            return

    if directory_name == '/':
        target_id = 1
    elif directory_name == '..':
        cursor.execute('''
        SELECT parent_id FROM filesystem
        WHERE id = ?
        ''', (current_directory_id,))
        parent = cursor.fetchone()
        if parent and parent[0]:
            target_id = parent[0]
        else:
            print("Already at root directory.")
            return
    else:
        cursor.execute('''
        SELECT id FROM filesystem
        WHERE name = ? AND type = 'directory' AND parent_id = ?
        ''', (directory_name, current_directory_id))
        result = cursor.fetchone()
        if result:
            target_id = result[0]
        else:
            print(f"Directory '{directory_name}' not found.")
            return

    if has_permission(target_id, 'execute'):
        current_directory_id = target_id
    else:
        print("Permission denied.")

#Print Working Directory
def pwd():
    path = get_current_directory_path()
    print(path)

def is_absolute_path(path):
    return path.startswith('/')

def join_paths(base_path, *paths):
    full_path = base_path.rstrip('/')
    for p in paths:
        full_path += '/' + p.strip('/')
    return full_path

def split_path(path):
    path = path.rstrip('/')
    if '/' in path:
        idx = path.rfind('/')
        parent = path[:idx] if idx != 0 else '/'
        name = path[idx+1:]
    else:
        parent = ''
        name = path
    return parent, name

#Returns ID for files and Directories
def get_item_id_by_path(path, current_dir_id=None):
    # Determine if the path is absolute or relative
    if is_absolute_path(path):
        # Absolute path: Start from root
        dir_id = 1  # Root directory ID
    else:
        # Relative path: Start from current directory
        if current_dir_id is None:
            current_dir_id = current_directory_id
        dir_id = current_dir_id

    # Split the path into parts
    parts = [p for p in path.strip('/').split('/') if p]

    # Traverse the path
    for part in parts:
        cursor.execute('''
        SELECT id FROM filesystem
        WHERE name = ? AND parent_id = ?
        ''', (part, dir_id))
        result = cursor.fetchone()
        if result:
            dir_id = result[0]
        else:
            return None  # Path does not exist
    return dir_id

def get_parent_id(item_id):
    cursor.execute('SELECT parent_id FROM filesystem WHERE id = ?', (item_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_name_by_id(item_id):
    cursor.execute('SELECT name FROM filesystem WHERE id = ?', (item_id,))
    result = cursor.fetchone()
    return result[0] if result else None

#Copy functions
def cp(source_path, destination_path, recursive=False):
    if not current_user:
        print("No user logged in.")
        return

    # Resolve source path
    source_item_id = get_item_id_by_path(source_path, current_directory_id)
    if not source_item_id:
        print(f"cp: cannot stat '{source_path}': No such file or directory")
        return

    # Get source item details
    cursor.execute('''
    SELECT name, type, parent_id, owner_id, permissions, content, size, modification_date
    FROM filesystem WHERE id = ?
    ''', (source_item_id,))
    source_item = cursor.fetchone()
    if not source_item:
        print(f"cp: cannot stat '{source_path}': No such file or directory")
        return

    source_name, source_type, source_parent_id, source_owner_id, source_permissions, source_content, source_size, source_modification_date = source_item

    # Check read permission on source
    if not has_permission(source_item_id, 'read'):
        print(f"cp: cannot open '{source_path}': Permission denied")
        return

    # Resolve destination path
    destination_item_id = get_item_id_by_path(destination_path, current_directory_id)
    if destination_item_id:
        # Destination exists
        cursor.execute('SELECT type FROM filesystem WHERE id = ?', (destination_item_id,))
        dest_type = cursor.fetchone()[0]
        if dest_type == 'directory':
            # Copy into the directory
            destination_parent_id = destination_item_id
            destination_name = source_name
        else:
            # Destination is a file, overwrite it or handle accordingly
            destination_parent_id = get_parent_id(destination_item_id)
            destination_name = get_name_by_id(destination_item_id)
    else:
        # Destination does not exist; determine parent directory and new name
        parent_path, destination_name = split_path(destination_path)
        if not parent_path:
            destination_parent_id = current_directory_id
        else:
            parent_id = get_item_id_by_path(parent_path, current_directory_id)
            if not parent_id:
                print(f"cp: cannot create '{destination_path}': No such file or directory")
                return
            destination_parent_id = parent_id

    # Check write permission on destination directory
    if not has_permission(destination_parent_id, 'write'):
        print(f"cp: cannot create '{destination_path}': Permission denied")
        return

    # If copying a directory without recursive option
    if source_type == 'directory' and not recursive:
        print(f"cp: -r not specified; omitting directory '{source_path}'")
        return

    # Perform the copy
    if source_type == 'file':
        copy_file(source_item_id, destination_parent_id, destination_name)
    else:
        copy_directory(source_item_id, destination_parent_id, destination_name)

#Checks for file name and retrieves attributes and content with entry.
def copy_file(source_id, destination_parent_id, destination_name):
    # Check if a file with the same name exists in the destination directory
    cursor.execute('''
    SELECT id FROM filesystem
    WHERE name = ? AND parent_id = ?
    ''', (destination_name, destination_parent_id))
    if cursor.fetchone():
        print(f"cp: cannot create file '{destination_name}': File exists")
        return

    # Get source file details
    cursor.execute('''
    SELECT content, permissions, size
    FROM filesystem WHERE id = ?
    ''', (source_id,))
    source_content, source_permissions, source_size = cursor.fetchone()

    now = datetime.datetime.now().isoformat()
    try:
        cursor.execute('''
        INSERT INTO filesystem (name, type, content, parent_id, owner_id, permissions, size, modification_date)
        VALUES (?, 'file', ?, ?, ?, ?, ?, ?)
        ''', (destination_name, source_content, destination_parent_id, current_user['id'], source_permissions, source_size, now))
        conn.commit()
        print(f"File '{destination_name}' copied.")
    except sqlite3.IntegrityError as e:
        print(f"Error: {e}")

def copy_directory(source_id, destination_parent_id, destination_name):
    # Recursively copy a directory
    # Check if a directory with the same name exists in the destination directory
    cursor.execute('''
    SELECT id FROM filesystem
    WHERE name = ? AND parent_id = ?
    ''', (destination_name, destination_parent_id))
    if cursor.fetchone():
        print(f"cp: cannot create directory '{destination_name}': Directory exists")
        return

    # Get source directory details
    cursor.execute('''
    SELECT permissions
    FROM filesystem WHERE id = ?
    ''', (source_id,))
    source_permissions = cursor.fetchone()[0]

    now = datetime.datetime.now().isoformat()
    try:
        # Create the directory
        cursor.execute('''
        INSERT INTO filesystem (name, type, parent_id, owner_id, permissions, size, modification_date)
        VALUES (?, 'directory', ?, ?, ?, ?, ?)
        ''', (destination_name, destination_parent_id, current_user['id'], source_permissions, 0, now))
        conn.commit()
        new_directory_id = cursor.lastrowid

        # Recursively copy contents
        cursor.execute('''
        SELECT id, name, type FROM filesystem WHERE parent_id = ?
        ''', (source_id,))
        items = cursor.fetchall()
        for item in items:
            item_id, item_name, item_type = item
            if item_type == 'file':
                copy_file(item_id, new_directory_id, item_name)
            else:
                copy_directory(item_id, new_directory_id, item_name)
    except sqlite3.IntegrityError as e:
        print(f"Error: {e}")

def mv(source_path, destination_path):
    if not current_user:
        print("No user logged in.")
        return

    # Resolve source path
    source_item_id = get_item_id_by_path(source_path, current_directory_id)
    if not source_item_id:
        print(f"mv: cannot stat '{source_path}': No such file or directory")
        return

    # Get source item details
    cursor.execute('''
    SELECT name, type, parent_id, owner_id, permissions
    FROM filesystem WHERE id = ?
    ''', (source_item_id,))
    source_item = cursor.fetchone()
    if not source_item:
        print(f"mv: cannot stat '{source_path}': No such file or directory")
        return

    source_name, source_type, source_parent_id, source_owner_id, source_permissions = source_item

    # Check write permission on source parent directory
    if not has_permission(source_parent_id, 'write'):
        print(f"mv: cannot move '{source_path}': Permission denied")
        return

    # Resolve destination path
    destination_item_id = get_item_id_by_path(destination_path, current_directory_id)

    if destination_item_id:
        # Destination exists
        cursor.execute('SELECT type FROM filesystem WHERE id = ?', (destination_item_id,))
        dest_type = cursor.fetchone()[0]
        if dest_type == 'directory':
            # Move into the directory
            destination_parent_id = destination_item_id
            destination_name = source_name
        else:
            # Destination is a file or directory; prevent overwriting
            print(f"mv: cannot move '{source_path}': Destination '{destination_path}' already exists")
            return
    else:
        # Destination does not exist; determine parent directory and new name
        parent_path, destination_name = split_path(destination_path)
        if not parent_path:
            destination_parent_id = current_directory_id
        else:
            parent_id = get_item_id_by_path(parent_path, current_directory_id)
            if not parent_id:
                print(f"mv: cannot move '{source_path}': No such directory '{parent_path}'")
                return
            destination_parent_id = parent_id

    # Check write permission on destination directory
    if not has_permission(destination_parent_id, 'write'):
        print(f"mv: cannot move '{source_path}': Permission denied")
        return

    # Prevent moving a directory into one of its subdirectories
    if source_type == 'directory':
        if is_subdirectory(source_item_id, destination_parent_id):
            print(f"mv: cannot move '{source_path}': Cannot move a directory into one of its subdirectories")
            return

    # Update the item's parent_id and name to move/rename it
    try:
        now = datetime.datetime.now().isoformat()
        cursor.execute('''
        UPDATE filesystem
        SET parent_id = ?, name = ?, modification_date = ?
        WHERE id = ?
        ''', (destination_parent_id, destination_name, now, source_item_id))
        conn.commit()
        print(f"'{source_path}' has been moved to '{destination_path}'")
    except sqlite3.IntegrityError as e:
        print(f"Error: {e}")

def is_subdirectory(source_id, destination_id):
    if source_id == destination_id:
        return True
    cursor.execute('SELECT parent_id FROM filesystem WHERE id = ?', (destination_id,))
    result = cursor.fetchone()
    if result:
        parent_id = result[0]
        if parent_id is None:
            return False
        return is_subdirectory(source_id, parent_id)
    else:
        return False

def head(params):
    if not current_user:
        print("No user logged in.")
        return

    num_lines = 10  # Default number of lines
    filename = None

    # Parse command-line options
    if not params:
        print("Usage: head [-number_of_lines] <file_name>")
        return

    if params[0].startswith('-') and len(params[0]) > 1 and params[0][1:].isdigit():
        num_lines = int(params[0][1:])
        if len(params) == 2:
            filename = params[1]
        else:
            print("Usage: head [-number_of_lines] <file_name>")
            return
    else:
        filename = params[0]

    # Resolve the file path
    file_id = get_item_id_by_path(filename, current_directory_id)
    if not file_id:
        print(f"head: cannot open '{filename}': No such file")
        return

    # Check if it's a file
    cursor.execute('SELECT type FROM filesystem WHERE id = ?', (file_id,))
    item_type = cursor.fetchone()[0]
    if item_type != 'file':
        print(f"head: '{filename}' is not a file")
        return

    # Check read permission
    if not has_permission(file_id, 'read'):
        print(f"head: cannot open '{filename}': Permission denied")
        return

    # Get file content
    cursor.execute('SELECT content FROM filesystem WHERE id = ?', (file_id,))
    content = cursor.fetchone()[0]
    lines = content.split('\n')

    # Display the first 'n' lines
    for line in lines[:num_lines]:
        print(line)

def tail(params):
    if not current_user:
        print("No user logged in.")
        return

    num_lines = 10  # Default number of lines
    filename = None

    # Parse command-line options
    if not params:
        print("Usage: tail [-number_of_lines] <file_name>")
        return

    if params[0].startswith('-') and len(params[0]) > 1 and params[0][1:].isdigit():
        num_lines = int(params[0][1:])
        if len(params) == 2:
            filename = params[1]
        else:
            print("Usage: tail [-number_of_lines] <file_name>")
            return
    else:
        filename = params[0]

    # Resolve the file path
    file_id = get_item_id_by_path(filename, current_directory_id)
    if not file_id:
        print(f"tail: cannot open '{filename}': No such file")
        return

    # Check if it's a file
    cursor.execute('SELECT type FROM filesystem WHERE id = ?', (file_id,))
    item_type = cursor.fetchone()[0]
    if item_type != 'file':
        print(f"tail: '{filename}' is not a file")
        return

    # Check read permission
    if not has_permission(file_id, 'read'):
        print(f"tail: cannot open '{filename}': Permission denied")
        return

    # Get file content
    cursor.execute('SELECT content FROM filesystem WHERE id = ?', (file_id,))
    content = cursor.fetchone()[0]
    lines = content.split('\n')

    # Display the last 'n' lines
    for line in lines[-num_lines:]:
        print(line)

def parse_head_tail_params(params, command_name):
    num_lines = 10  # Default number of lines
    filename = None

    if len(params) == 1:
        filename = params[0]
    elif len(params) == 3 and params[0] == '-n':
        try:
            num_lines = int(params[1])
            if num_lines < 0:
                print(f"{command_name}: invalid number of lines: '{num_lines}'")
                return None, None
        except ValueError:
            print(f"{command_name}: invalid number of lines")
            return None, None
        filename = params[2]
    else:
        print(f"Usage: {command_name} [-n number_of_lines] <file_name>")
        return None, None

    return num_lines, filename

def grep(params):
    if not current_user:
        print("No user logged in.")
        return

    # Initialize options
    case_insensitive = False
    line_numbers = False
    patterns = []
    filenames = []

    # Parse options and arguments
    idx = 0
    while idx < len(params):
        param = params[idx]
        if param.startswith('-'):
            if 'i' in param:
                case_insensitive = True
            if 'n' in param:
                line_numbers = True
            idx += 1
        else:
            break  # Options are over
    if idx >= len(params):
        print("Usage: grep [options] <pattern> <file1> [file2 ...]")
        return
    else:
        # The next parameter is the pattern
        pattern = params[idx]
        idx += 1
        # Remaining parameters are filenames
        filenames = params[idx:]

    if not pattern or not filenames:
        print("Usage: grep [options] <pattern> <file1> [file2 ...]")
        return

    # Compile the pattern
    flags = re.IGNORECASE if case_insensitive else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        print(f"grep: invalid regular expression: {e}")
        return

    # Search in each file
    for filename in filenames:
        file_id = get_item_id_by_path(filename, current_directory_id)
        if not file_id:
            print(f"grep: {filename}: No such file")
            continue

        # Check if it's a file
        cursor.execute('SELECT type FROM filesystem WHERE id = ?', (file_id,))
        item_type = cursor.fetchone()[0]
        if item_type != 'file':
            print(f"grep: {filename}: Is not a file")
            continue

        # Check read permission
        if not has_permission(file_id, 'read'):
            print(f"grep: {filename}: Permission denied")
            continue

        # Get file content
        cursor.execute('SELECT content FROM filesystem WHERE id = ?', (file_id,))
        content = cursor.fetchone()[0]
        lines = content.split('\n')

        # Search for the pattern in each line
        for line_number, line in enumerate(lines, start=1):
            if regex.search(line):
                output = ''
                if len(filenames) > 1:
                    output += f"{filename}:"
                if line_numbers:
                    output += f"{line_number}:"
                output += line
                print(output)

def touch(file_name):
    if not current_user:
        print("No user logged in.")
        return
    if not has_permission(current_directory_id, 'write'):
        print("Permission denied.")
        return
    # Check if the file already exists
    cursor.execute('''
    SELECT id FROM filesystem
    WHERE name = ? AND type = 'file' AND parent_id = ?
    ''', (file_name, current_directory_id))
    if cursor.fetchone():
        print(f"Error: File '{file_name}' already exists.")
        return
    try:
        now = datetime.datetime.now().isoformat()
        cursor.execute('''
        INSERT INTO filesystem (name, type, parent_id, owner_id, content, size, modification_date)
        VALUES (?, 'file', ?, ?, '', ?, ?)
        ''', (file_name, current_directory_id, current_user['id'], 0, now))
        conn.commit()
        print(f"File '{file_name}' created.")
    except sqlite3.IntegrityError as e:
        print(f"Error: {e}")

def rm(name):
    if not current_user:
        print("No user logged in.")
        return
    if not has_permission(current_directory_id, 'write'):
        print("Permission denied.")
        return
    cursor.execute('''
    SELECT id, type FROM filesystem
    WHERE name = ? AND parent_id = ?
    ''', (name, current_directory_id))
    item = cursor.fetchone()
    if item:
        item_id, item_type = item
        if not has_permission(item_id, 'write'):
            print("Permission denied.")
            return
        if item_type == 'directory':
            delete_directory(item_id)
        else:
            cursor.execute('DELETE FROM filesystem WHERE id = ?', (item_id,))
        conn.commit()
        print(f"'{name}' has been removed.")
    else:
        print("Item not found.")

def delete_directory(dir_id):
    if not has_permission(dir_id, 'write') or not has_permission(dir_id, 'execute'):
        print("Permission denied.")
        return
    cursor.execute('''
    SELECT id, type FROM filesystem
    WHERE parent_id = ?
    ''', (dir_id,))
    items = cursor.fetchall()
    for item in items:
        item_id, item_type = item
        if item_type == 'directory':
            delete_directory(item_id)
        else:
            if has_permission(item_id, 'write'):
                cursor.execute('DELETE FROM filesystem WHERE id = ?', (item_id,))
            else:
                print(f"Permission denied to delete item with ID '{item_id}'.")
    cursor.execute('DELETE FROM filesystem WHERE id = ?', (dir_id,))

def cat(params):
    if not current_user:
        print("No user logged in.")
        return ''

    output_data = ''

    if len(params) < 1:
        print("Usage: cat <file1> [file2 ...]")
        return ''

    for file_name in params:
        #print(f"Debug: Attempting to cat '{file_name}'")  # Debugging

        # Resolve the file path
        file_id = get_item_id_by_path(file_name, current_directory_id)
        if not file_id:
            print(f"cat: cannot open '{file_name}': No such file")
            continue

        # Check if it's a file
        cursor.execute('SELECT type FROM filesystem WHERE id = ?', (file_id,))
        result = cursor.fetchone()
        if not result:
            print(f"cat: '{file_name}' does not exist in the filesystem.")
            continue

        item_type = result[0]
        if item_type != 'file':
            print(f"cat: '{file_name}' is not a file")
            continue

        # Check read permission
        if not has_permission(file_id, 'read'):
            print(f"cat: cannot open '{file_name}': Permission denied")
            continue

        # Get file content
        cursor.execute('SELECT content FROM filesystem WHERE id = ?', (file_id,))
        content_result = cursor.fetchone()
        if content_result is None:
            print(f"cat: cannot retrieve content from '{file_name}'")
            continue

        content = content_result[0]
        #print(f"Debug: Retrieved content from '{file_name}': {content}")  # Debugging

        output_data += content + '\n'

    return output_data.rstrip('\n')

def view_file_content(file_name):
    file_id = get_item_id_by_path(file_name, current_directory_id)
    if not file_id:
        print(f"No such file: {file_name}")
        return

    cursor.execute('SELECT content FROM filesystem WHERE id = ?', (file_id,))
    result = cursor.fetchone()
    if result:
        print(f"Content of '{file_name}':")
        print(result[0])
    else:
        print(f"No content found for '{file_name}'")


def write(params):
    if not current_user:
        print("No user logged in.")
        return
    if len(params) != 1:
        print("Usage: write <file_name>")
        return
    file_name = params[0]

    file_id = get_item_id_by_path(file_name, current_directory_id)
    if not file_id:
        # File does not exist, create it
        touch(file_name)
        file_id = get_item_id_by_path(file_name, current_directory_id)

    # Check write permission
    if not has_permission(file_id, 'write'):
        print(f"write: cannot write to '{file_name}': Permission denied")
        return

    print("Enter text. Type 'EOF' on a new line to finish.")
    lines = []
    while True:
        line = input()
        if line == 'EOF':
            break
        lines.append(line)
    content = '\n'.join(lines)

    now = datetime.datetime.now().isoformat()
    cursor.execute('''
    UPDATE filesystem
    SET content = ?, size = ?, modification_date = ?
    WHERE id = ?
    ''', (content, len(content), now, file_id))
    conn.commit()
    print(f"Content written to '{file_name}'")

def echo(params):
    if not current_user:
        print("No user logged in.")
        return
    if len(params) < 2:
        print("Usage: echo <file_name> <content>")
        return
    file_name = params[0]
    content = ' '.join(params[1:])

    # Interpret escape sequences
    content = interpret_escape_sequences(content)

    # Resolve the file path
    file_id = get_item_id_by_path(file_name, current_directory_id)
    if not file_id:
        # File does not exist, create it
        touch(file_name)
        file_id = get_item_id_by_path(file_name, current_directory_id)

    # Check write permission
    if not has_permission(file_id, 'write'):
        print(f"echo: cannot write to '{file_name}': Permission denied")
        return

    now = datetime.datetime.now().isoformat()
    cursor.execute('''
    UPDATE filesystem
    SET content = ?, size = ?, modification_date = ?
    WHERE id = ?
    ''', (content, len(content), now, file_id))
    conn.commit()
    print(f"Content written to '{file_name}'")

def wc(params):
    if not current_user:
        print("No user logged in.")
        return

    # Initialize options
    count_lines = False
    count_words = False
    count_chars = False
    filenames = []

    # Default behavior: if no flags are provided, count lines, words, and characters
    default_behavior = True

    # Parse options and arguments
    idx = 0
    while idx < len(params):
        param = params[idx]
        if param.startswith('-'):
            default_behavior = False  # User has specified flags
            if 'l' in param:
                count_lines = True
            if 'w' in param:
                count_words = True
            if 'c' in param:
                count_chars = True
            idx += 1
        else:
            break  # Options are over
    filenames = params[idx:]

    if not filenames:
        print("Usage: wc [options] <file1> [file2 ...]")
        return

    if default_behavior:
        count_lines = True
        count_words = True
        count_chars = True

    total_lines = 0
    total_words = 0
    total_chars = 0

    # Process each file
    for filename in filenames:
        file_id = get_item_id_by_path(filename, current_directory_id)
        if not file_id:
            print(f"wc: {filename}: No such file")
            continue

        # Check if it's a file
        cursor.execute('SELECT type FROM filesystem WHERE id = ?', (file_id,))
        item_type = cursor.fetchone()[0]
        if item_type != 'file':
            print(f"wc: {filename}: Is not a file")
            continue

        # Check read permission
        if not has_permission(file_id, 'read'):
            print(f"wc: {filename}: Permission denied")
            continue

        # Get file content
        cursor.execute('SELECT content FROM filesystem WHERE id = ?', (file_id,))
        content = cursor.fetchone()[0]
        lines = content.split('\n')
        words = content.split()
        chars = len(content)

        num_lines = len(lines)
        num_words = len(words)
        num_chars = chars

        total_lines += num_lines
        total_words += num_words
        total_chars += num_chars

        # Build output string
        output_parts = []
        if count_lines:
            output_parts.append(f"{num_lines}")
        if count_words:
            output_parts.append(f"{num_words}")
        if count_chars:
            output_parts.append(f"{num_chars}")
        output_parts.append(filename)
        print('\t'.join(output_parts))

    # If multiple files, print total
    if len(filenames) > 1:
        output_parts = []
        if count_lines:
            output_parts.append(f"{total_lines}")
        if count_words:
            output_parts.append(f"{total_words}")
        if count_chars:
            output_parts.append(f"{total_chars}")
        output_parts.append("total")
        print('\t'.join(output_parts))

def interpret_escape_sequences(s):
    escape_sequences = {
        r'\n': '\n',
        r'\t': '\t',
        r'\\': '\\',
        r'\'': '\'',
        r'\"': '\"',
    }
    pattern = re.compile('|'.join(map(re.escape, escape_sequences.keys())))
    return pattern.sub(lambda m: escape_sequences[m.group()], s)

def chmod(name, permissions):
    if not current_user:
        print("No user logged in.")
        return
    cursor.execute('''
    SELECT id, owner_id FROM filesystem
    WHERE name = ? AND parent_id = ?
    ''', (name, current_directory_id))
    item = cursor.fetchone()
    if item:
        item_id, owner_id = item
        if current_user['id'] == owner_id or current_user['id'] == 1:
            cursor.execute('''
            UPDATE filesystem SET permissions = ?
            WHERE id = ?
            ''', (permissions, item_id))
            conn.commit()
            print(f"Permissions of '{name}' changed to '{permissions}'.")
        else:
            print("Permission denied.")
    else:
        print("Item not found.")

# Shell code to implement commands
def shell():
    global current_user
    load_history()
    try:
        while True:
            if current_user:
                prompt = f"{current_user['username']}:{get_current_directory_path()}$ "
            else:
                prompt = "guest_user$ "
            try:
                command_line = input(prompt)
                if not command_line.strip():
                    continue
                args = command_line.strip().split()
                command = args[0]
                params = args[1:]

                if command == 'exit':
                    print("Exiting shell.")
                    break
                
                elif command == 'grep':
                    grep(params)

                elif command == 'register':
                    if len(params) != 0:
                        print("Usage: register")
                    else:
                        username = input("Enter new username: ")
                        password = getpass.getpass("Enter new password: ")
                        # Confirm password
                        confirm_password = getpass.getpass("Confirm password: ")
                        if password != confirm_password:
                            print("Passwords do not match. Registration aborted.")
                            continue
                        register(username, password)

                elif command == 'login':
                    if len(params) != 0:
                        print("Usage: login")
                    else:
                        username = input("Enter username: ")
                        password = getpass.getpass("Enter password: ")
                        login(username, password)

                elif command == 'logout':
                    logout()
                
                elif command == 'ls':
                    ls(params)  # Pass parameters to ls function
                    
                elif command == 'pwd':
                    if params:
                        print("Usage:pwd")
                    else:
                        pwd()

                elif command == 'cd':
                    if len(params) > 1:
                        print("Usage: cd [directory]")
                    else:
                        directory_name = params[0] if params else None
                        cd(directory_name)

                elif command == 'mkdir':
                    if len(params) != 1:
                        print("Usage: mkdir <directory_name>")
                    else:
                        mkdir(params[0])
                        
                elif command == 'cp':
                    if len(params) < 2:
                        print("Usage: cp [-r] <source> <destination>")
                    else: 
                        recursive = False
                        if params[0] == '-r':
                            recursive = True
                            params = params[1:]
                        if len(params) !=2:
                            print("Usage: cp [-r] <source> <destination>")
                        else:
                            source_path = params[0]
                            destination_path = params[1]
                            cp(source_path, destination_path, recursive)
                
                elif command == 'mv':
                    if len(params) != 2:
                        print("Usage: mv <source> <destination>")
                    else:
                        source_path = params[0]
                        destination_path = params[1]
                        mv(source_path, destination_path)
                
                elif command == 'head':
                    head(params)

                elif command == 'tail':
                    tail(params)

                elif command == 'touch':
                    if len(params) != 1:
                        print("Usage: touch <file_name>")
                    else:
                        touch(params[0])

                elif command == 'rm':
                    if len(params) != 1:
                        print("Usage: rm <file_or_directory>")
                    else:
                        rm(params[0])
                        
                elif command == 'cat':
                    if len(params) < 1:
                        print("Usage: cat <file1> [file2 ...]")
                    else:
                        output_data = cat(params)
                        if output_data:
                            print(output_data)
                    
                    
                elif command == 'write':
                    write(params)

                ##/elif command == 'cat':
                    #if len(params) != 1:
                    #   print("Usage: cat <file_name>")
                    #else:
                    #   cat(params[0])] 

                elif command == 'echo':
                    if len(params) < 2:
                        print("Usage: echo <file_name> <content>")
                    else:
                        echo(params)
                        
                elif command == 'wc':
                    wc(params)

                elif command == 'chmod':
                    if len(params) != 2:
                        print("Usage: chmod <permissions> <file_or_directory>")
                    else:
                        chmod(params[1], params[0])

                else:
                    print(f"Unknown command: {command}")
                    
            except KeyboardInterrupt:
                print("\nUse 'exit' to quit the shell.")
            except EOFError:
                print("\nExiting shell.")
                break
            except Exception as e:
                print(f"Error: {e}")
    finally:
        save_history()

# Start the shell
if __name__ == "__main__":
    print("Welcome to the shell, type register to create an account\nOtherwise type login to begin login process.\nWhen finished type exit to quit shell.")
    shell()
    conn.close()
