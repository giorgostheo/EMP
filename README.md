# Edge Management Platform (EMP) v0.1

Manage and execute tasks across multiple hosts

## Description

EMP is a command-line tool for managing and executing tasks across multiple remote hosts. It provides an interface to define, synchronize, deploy, and execute modules on connected devices.

## Installation

Clone this repository and install dependencies:

```bash
git clone https://github.com/yourusername/EMP.git
cd EMP
pip install -r requirements.txt
```

## Usage

Run the CLI tool:

```bash
python emp [command] [options]
```

### Basic Commands

1. Display help message with available commands:

    ```bash
    python emp --help
    ```

2. Execute a command on a specific host:

    ```bash
    python emp command HOSTNAME  "ls -la"
    ```

3. Deploy a module to a specific host:

    ```bash
    python emp deploy HOSTNAME  ./path/to/module_directory
    ```

### Advanced Commands

4. Open an interactive TTY session with a host:

    ```bash
    python emp tty HOSTNAME 
    ```

5. Check the status of all connected hosts:

    ```bash
    python emp check
    ```

## Configuration

Edit the following configuration files to set up and customize EMP:

- `hosts.json`: Define remote hosts and their connection details (hostname, port, username, password)
- `requirements.txt`: List Python dependencies for the CLI tool
- `_version.py`: Set the version number of the package

## Environment Variables

- V (int): Logging verbosity level (0=ERROR, 1=INFO, 2=DEBUG)
- RB (int): Rebuild flag (0 or 1)
- DT (int): Detached execution flag (0 or 1)

### Logging Levels

Control verbosity using the `V` environment variable:

```bash
# Default (show errors only)
V=0 python emp deploy HOSTNAME MODULE

# Standard level (info, warnings, errors)
V=1 python emp deploy HOSTNAME MODULE

# Detailed debugging output
V=2 python emp deploy HOSTNAME MODULE
```

## Module Structure

Modules are organized in the `modules/` directory. Each module should contain:
- Python scripts (e.g., `main.py`)
- Shell scripts (`run.sh` for execution)
- Requirements files if needed

Example structure:

```
modules/
└── hello_world/
    ├── init.sh
    ├── main.py
    ├── requirements.txt
    └── run.sh
```

## Interactive Shell Access

EMP provides interactive shell access to remote hosts through its TTY command. This allows for direct interaction with the host's command line.

Example:

```bash
python emp tty HOSTNAME 
```

## Key Features

- **Multi-host management**: Connect to and manage multiple remote devices
- **Parallel execution**: Run commands across all connected nodes simultaneously
- **Interactive access**: Open TTY sessions for direct command-line interaction
- **Module deployment**: Deploy Python modules to remote hosts with version tracking
- **Configuration flexibility**: Customize behavior through environment variables

## Development

The project is currently in version 0.1 and is actively being developed. Contributions and feedback are welcome!

### License

This project is licensed under the MIT License - see the LICENSE file for details.