# EMP

Edge Management Platform - Create and deploy modules to the edge.

## Description

EMP is a command-line tool for managing and deploying Python modules to remote hosts. It provides a flexible framework for creating, versioning, and executing custom modules across multiple devices.

## Installation

Clone this repository and install dependencies:

```bash
git clone https://github.com/yourusername/emp-cli.git
cd emp-cli
pip install -r requirements.txt
```

## Usage

Run the CLI tool:

```Shell
python emp.py
```

## Features

- Connect to multiple remote hosts defined in `hosts.json`
- Deploy and execute Python modules on connected devices
- Version control for module updates
- Parallel execution of commands across multiple nodes
- Interactive shell access to remote hosts
- Configurable logging verbosity

### Logging Configuration

EMP uses the `V` environment variable to control logging levels:

```bash
# Show only errors (default behavior)
V=0 python emp myhost.local -f commands.txt

# Show INFO, WARNING, ERROR, CRITICAL messages
V=1 python emp myhost.local -f commands.txt

# Show all logs including DEBUG information
V=2 python emp myhost.local -f commands.txt
```

### Available Commands

Main features include:
- Module management: deploy, update, and run modules on remote devices
- Node management: connect to and manage multiple remote hosts
- Task automation: execute shell commands across connected nodes

#### Example Usage

1. Display help message with available commands:

    ```bash
    python emp --help
    ```

2. Execute a command on a specific host:

    ```bash
    python emp command HOSTNAME "ls -la"
    ```

3. Deploy a module to all connected hosts (specify directory):

    ```bash
    python emp deploy HOSTNAME ./path/to/module_directory
    ```

## Configuration

Edit the following files to configure EMP:

- `hosts.json`: Define remote hosts and their connection details
- `requirements.txt`: List Python dependencies for the CLI tool
- `setup.py`: Configure package settings

## Environment Variables

- V (int): Logging verbosity level (0=ERROR, 1=INFO, 2=DEBUG)
- RB (int): Rebuild flag (0 or 1)
- DT (int): Detached execution flag (0 or 1)

## Module Structure

Modules are organized in the `modules/` directory. Each module should contain:
- Python scripts (e.g., `main.py`)
- Shell scripts (`run.sh` for execution)
- Requirements files if needed

Example module structure:

```
modules/
└── hello_world/
    ├── init.sh
    ├── main.py
    ├── requirements.txt
    └── run.sh
```

## Development

This project is under active development. Contributions are welcome!

## Implemented Features

- Module deployment: Deploy directories as modules to remote hosts
- Command execution: Execute commands on specific hosts or all connected nodes
- TTY access: Open interactive terminal sessions with remote hosts
- Status checking: Verify module status through checkall command
- Help system: Display help messages with `emp` and `emp --help`