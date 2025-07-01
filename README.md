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

### Available Commands

Main features include:
- Module management: deploy, update, and run modules on remote devices
- Node management: connect to and manage multiple remote hosts
- Task automation: execute shell commands across connected nodes

### Example Usage

1. Display help message with available commands:

    ```bash
    python emp --help
    ```

2. Execute a command on a specific host:

    ```bash
    python emp command alpha "ls -la"
    ```

3. Deploy a module to all connected hosts (specify directory):

    ```bash
    python emp deploy my_module ./path/to/module_directory
    ```

### Roadmap

Completed:
- Module deployment to remote hosts
- Command execution on specific or all hosts
- TTY access for interactive terminal sessions
- Status checking via checkall command
- Help system implementation

Remaining:
- Improve command structure with unified interface for node operations
- Add module version tracking and rollback functionality
- Implement secure password handling (replace plaintext in hosts.json)
- Enhance error handling and recovery mechanisms
- Develop web-based UI for managing nodes and modules

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

## Configuration

Edit the following files to configure EMP:

- `hosts.json`: Define remote hosts and their connection details
- `requirements.txt`: List Python dependencies for the CLI tool
- `setup.py`: Configure package settings

## Development

This project is under active development. Contributions are welcome!

## Implemented Features

- Module deployment: Deploy directories as modules to remote hosts
- Command execution: Execute commands on specific hosts or all connected nodes
- TTY access: Open interactive terminal sessions with remote hosts
- Status checking: Verify module status through checkall command
- Help system: Display help messages with `emp` and `emp --help`