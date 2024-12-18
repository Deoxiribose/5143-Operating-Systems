# Dictionary containing help texts for each command
COMMAND_HELP = {
    "exit": "Usage: exit\nExits the shell.",
    "register": "Usage: register\nGuides you through the process of registering a new user.",
    "login": "Usage: login\nGuides you through the process of logging in.",
    "logout": "Usage: logout\nLogs out the current user.",
    "pwd": "Usage: pwd\nPrints the current working directory.",
    "ls": "Usage: ls [-a] [-l] [-h]\nLists directory contents.",
    "cd": "Usage: cd [directory]\nChanges the current working directory to the specified directory.\nIf no directory is given, it changes to the user's home directory.",
    "mkdir": "Usage: mkdir <directory_name>\nCreates a new directory.",
    "touch": "Usage: touch <file_name>\nCreates a new empty file.",
    "cat": "Usage: cat <file1> [file2 ...]\nPrints the contents of specified file(s).",
    "echo": "Usage: echo <file_name> <content>\nWrites the given content to the specified file.",
    "cp": "Usage: cp [-r] <source> <destination>\nCopies a file or directory from source to destination. Use -r for recursive copy.",
    "mv": "Usage: mv <source> <destination>\nMoves or renames a file or directory.",
    "rm": "Usage: rm <file_or_directory>\nRemoves a file or directory (recursively).",
    "chmod": "Usage: chmod <permissions> <file_or_directory>\nChanges the permissions of a file or directory.",
    "head": "Usage: head [-<number_of_lines>] <file_name>\nPrints the first lines of a file.",
    "tail": "Usage: tail [-<number_of_lines>] <file_name>\nPrints the last lines of a file.",
    "grep": "Usage: grep [options] <pattern> <file1> [file2 ...]\nSearches for a pattern in files.\nOptions:\n  -i: case-insensitive\n  -n: show line numbers",
    "wc": "Usage: wc [options] <file1> [file2 ...]\nCounts lines, words, and chars.\nOptions:\n  -l: line count\n  -w: word count\n  -c: char count",
    "write": "Usage: write <file_name>\nAllows interactive writing to a file.",
    "help": "Asking for help is crazy!"
}


def help_command(params):
    if not params:
        # If no command is specified, list all available commands
        print("Usage: help <command>\nAvailable commands:")
        for cmd in sorted(COMMAND_HELP.keys()):
            print(f"  {cmd}")
        return

    cmd = params[0]
    if cmd in COMMAND_HELP:
        print(COMMAND_HELP[cmd])
    else:
        print(f"No help available for '{cmd}'")
