#!/usr/bin/env python

import os, subprocess, shlex, sys, tty, termios, signal
from datetime import datetime

# Handle interrupts like Ctrl+C gracefully
def handle_signal(signal, frame):
    print("\nExiting shell.")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_signal)

def read_single_keypress():
    """Reads a single keypress from stdin and returns it"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)  # Read one character at a time
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def clear_line():
    """Clears the current line in the terminal"""
    sys.stdout.write("\r")  # Move the cursor to the start of the line
    sys.stdout.write("\033[K")  # Clear the line

def print_ls_description(show_hidden, long_format, human_readable):
    """Prints a description of the ls command based on flags"""
    description = "Listing contents of the directory"
    if show_hidden:
        description += " (including hidden files)"
    if long_format:
        description += " in long format"
    if human_readable:
        description += " with human-readable sizes"
    print(f"\033[35m{description}...\033[0m")  # Print description in purple

def custom_ls(args):
    """Custom implementation of the 'ls' command that separates files and directories"""
    path = "."
    show_hidden = False
    long_format = False
    human_readable = False

    # Parse flags
    for arg in args:
        if arg == "-a":
            show_hidden = True
        elif arg == "-l":
            long_format = True
        elif arg == "-h":
            human_readable = True
        else:
            path = arg  # Set custom path if provided

    # Print the command description in purple based on flags
    print_ls_description(show_hidden, long_format, human_readable)
    
    try:
        # Get the list of files
        files = os.listdir(path)
        files = sorted(files)  # Sort alphabetically


        # Separate files and folders
        file_list = []
        folder_list = []

        for f in files:
            if not show_hidden and f.startswith('.'):
                continue
            if os.path.isfile(os.path.join(path, f)):
                file_list.append(f)
            elif os.path.isdir(os.path.join(path, f)):
                folder_list.append(f)

        # Display files under the "Files" header (green)
        if file_list:
            print("\033[32mFiles\033[0m")  # Green "Files" header
            if long_format:
                for file in file_list:
                    file_path = os.path.join(path, file)
                    stats = os.stat(file_path)
                    permissions = get_file_permissions(stats.st_mode)
                    size = human_readable_size(stats.st_size) if human_readable else stats.st_size
                    modified_time = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M')
                    print(f"{permissions} {size:>10} {modified_time} {file}")
            else:
                print("\n".join(file_list))
            print()  # Newline for spacing

        # Display folders under the "Folders" header (orange)
        if folder_list:
            print("\033[33mFolders\033[0m")  # Orange "Folders" header
            if long_format:
                for folder in folder_list:
                    folder_path = os.path.join(path, folder)
                    stats = os.stat(folder_path)
                    permissions = get_file_permissions(stats.st_mode)
                    size = human_readable_size(stats.st_size) if human_readable else stats.st_size
                    modified_time = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M')
                    print(f"{permissions} {size:>10} {modified_time} {folder}")
            else:
                print("\n".join(folder_list))

    except FileNotFoundError:
        print(f"ls: cannot access '{path}': No such file or directory")

def get_file_permissions(mode):
    """Helper function to format file permissions"""
    is_dir = 'd' if os.path.isdir(mode) else '-'
    perm = ''
    perm += 'r' if mode & 0o400 else '-'
    perm += 'w' if mode & 0o200 else '-'
    perm += 'x' if mode & 0o100 else '-'
    perm += 'r' if mode & 0o040 else '-'
    perm += 'w' if mode & 0o020 else '-'
    perm += 'x' if mode & 0o010 else '-'
    perm += 'r' if mode & 0o004 else '-'
    perm += 'w' if mode & 0o002 else '-'
    perm += 'x' if mode & 0o001 else '-'
    return is_dir + perm

def create_directory(args):
    """Custom implementation of the mkdir command with visualization and confirmation"""
    if len(args) < 1:
        print("mkdir: missing directory name")
        return

    dir_name = args[0]
    path = os.path.abspath(dir_name)

    # Visualize the path
    print(f"\033[35mThe directory will be created at: {path}\033[0m")

    # Confirm directory creation
    confirm = input(f"Are you sure you want to create the directory '{dir_name}'? (y/n): ").lower()
    if confirm == 'y':
        try:
            os.makedirs(path, exist_ok=True)
            print(f"\033[32mDirectory '{dir_name}' created successfully!\033[0m")
        except Exception as e:
            print(f"\033[31mError creating directory '{dir_name}': {e}\033[0m")
    else:
        print("\033[31mDirectory creation canceled.\033[0m")

def process_command(command):
    """Process user commands"""
    args = shlex.split(command)
    
    if len(args) == 0:
        return

    # Custom 'ls' command
    if args[0] == "ls":
        custom_ls(args[1:])
    
    # Custom 'mkdir' command
    elif args[0] == "mkdir":
        create_directory(args[1:])

    # Handle built-in commands (e.g., cd, exit)
    elif args[0] == "exit":
        sys.exit(0)
    elif args[0] == "cd":
        try:
            os.chdir(args[1])
        except IndexError:
            print("cd: missing argument")
        except FileNotFoundError:
            print(f"cd: no such file or directory: {args[1]}")
    else:
        # Execute external commands
        try:
            subprocess.run(args)
        except FileNotFoundError:
            print(f"{args[0]}: command not found")
        except Exception as e:
            print(f"Error running command: {e}")

def shell():
    # Welcome message
    print("Welcome to my Python shell!")
    print("Type 'exit' to quit.")
    print("---------------------------")

    history = []  # To keep a history of commands
    history_index = -1  # To navigate through history
    current_command = ""

    while True:
        sys.stdout.write("my_shell$ ")  # Print shell prompt
        sys.stdout.flush()  # Ensure the prompt is shown
        current_command = ""
        history_index = len(history)  # Reset the history index

        while True:
            suggestion = ""  # No suggestion needed for now
            clear_line()  # Clear the line before re-printing
            sys.stdout.write(f"my_shell$ {current_command}")
            sys.stdout.flush()

            key = read_single_keypress()

            if key == '\x1b':  # Escape sequence for special keys (like arrows)
                key += sys.stdin.read(2)  # Read the rest of the escape sequence
                if key == '\x1b[A':  # Up arrow
                    if history and history_index > 0:
                        history_index -= 1
                        current_command = history[history_index]
                elif key == '\x1b[B':  # Down arrow
                    if history and history_index < len(history) - 1:
                        history_index += 1
                        current_command = history[history_index]
                    else:
                        current_command = ""
                        history_index = len(history)

            elif key == '\r':  # Enter key
                print()  # Move to a new line
                if current_command.strip():
                    history.append(current_command)  # Save to history
                    process_command(current_command)
                break

            elif key == '\x7f':  # Backspace key
                if len(current_command) > 0:
                    current_command = current_command[:-1]  # Remove last character

            else:
                current_command += key  # Add regular characters to the command

if __name__ == "__main__":
    shell()
