#!/usr/bin/env python3

# Import from the package structure
from ._version import __version__
from .commands import Interface
import sys

# Import logging configuration
import logging

logger = logging.getLogger(__name__)

import argparse
import os

def main():
    # Initialize the prompt session with history persistence

    # Set up command line argument parser with subparsers for commands
    parser = argparse.ArgumentParser(description="EMP - Edge Management Platform",
                                    epilog="Use 'emp --help' or 'emp <command> --help' for more information on a specific command.")

    # Add help/version arguments to the main parser
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose mode")
    parser.add_argument("--version", action="version",
                        version=f"EMP v{__version__}")

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Deploy command
    attached_parser = subparsers.add_parser('attached', help="Deploy a directory as a module and receive STDOUT")
    attached_parser.add_argument('host', help="Host to deploy module on")
    attached_parser.add_argument('directory', nargs='?', help="Directory to deploy")

    # Deploy command
    detached_parser = subparsers.add_parser('detached', help="Deploy a directory as a module using TMUX")
    detached_parser.add_argument('host', help="Host to deploy module on")
    detached_parser.add_argument('directory', nargs='?', help="Directory to deploy")

    # Command execution
    cmd_parser = subparsers.add_parser('command', help="Execute a command on a specific host")
    cmd_parser.add_argument('host', help="Host to execute command on")
    cmd_parser.add_argument('cmd_text', help="Command to execute")

    # TTY command
    tty_parser = subparsers.add_parser('tty', help="Open an interactive TTY session with a host")
    tty_parser.add_argument('host', help="Host to connect to")

    # Check command
    check_parser = subparsers.add_parser('check', help="Check module status on a specific host")

    # Parse arguments
    args, unknown = parser.parse_known_args()

    # Display help message if no command is provided or --help is used
    if not args.command and (unknown and '--help' in unknown) or not args.command:
        print("\nEMP - Edge Management Platform\n")
        print("Usage: python emp [command] [options]\n")
        print("Available commands:")
        parser.print_help()
        sys.exit()

    # Extract and process command line arguments
    module_name = os.path.basename(os.getcwd())  # Get the current module name from directory

    # Read environment variables for rebuild/detach options
    rebuild_flag = bool(int(os.getenv('RB', 0)))  # Rebuild flag

    # Initialize the interface with host connections
    host = args.host if 'host' in args else ''
    interface = Interface(host)

    # Handle different commands based on parsing results
    command = args.command if 'command' in args else ''

    if command == 'attached':
        if not args.directory:
            print("Usage: python emp deploy [<directory>]")
        else:
            directory = os.path.abspath(args.directory) # Get the directory name from path')

            interface.command_module_par(args.directory, rebuild_flag, False)
    elif command == 'detached':
        if not args.directory:
            print("Usage: python emp deploy [<directory>]")
        else:
            directory = os.path.abspath(args.directory) # Get the directory name from path')

            interface.command_module_par(args.directory, rebuild_flag, True)
    elif command == 'command':
        try:
            cmd_text = args.cmd_text
            interface.command_exec(cmd_text)
        except AttributeError:
            print("Usage: python emp command [<host>] [<command>]")
    elif command == 'tty':
        try:
            interface.command_tty(host)
        except AttributeError:
            print("Usage: python emp tty [<host>]")
    elif command == 'check':
        try:
            pass
            # interface.command_monitorall()
        except AttributeError:
            print("Usage: python emp check [<host>]")

if __name__ == "__main__":
    main()