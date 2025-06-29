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

Use the `ls` command to list all available commands:

```Shell
emp ls
```

Main features include:
- Module management: deploy, update, and run modules on remote devices
- Node management: connect to and manage multiple remote hosts
- Task automation: execute shell commands across connected nodes

### Example Usage

1. List available commands:

   ```Shell
   emp ls
   ```

2. Connect to a specific node:

   ```Shell
   emp checkall pi4
   ```

3. Deploy a module to all connected nodes:

   ```Shell
   emp module hello_world false true
   ```

### Roadmap

- Improve command structure by creating a unified interface for executing commands on all nodes
- Add support for module version tracking and rollbacks
- Implement secure password handling instead of plaintext in hosts.json
- Add more robust error handling and recovery mechanisms
- Create a web-based UI for managing nodes and modules

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

### TODO:
