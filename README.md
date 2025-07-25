# Edge Management Platform (EMP) v0.1

Manage and execute tasks across multiple hosts

## Description

EMP is a command-line tool for managing and executing tasks across multiple remote hosts. It provides an interface to define, synchronize, deploy, and execute modules on connected devices.

## Installation

You can install EMP either by cloning the repository or using pip.

### Method 1: Traditional Installation (from source)

Clone this repository and install dependencies:

```bash
git clone https://github.com/yourusername/EMP.git
cd EMP
pip install -r requirements.txt
```

### Method 2: Install via Pip

You can also install EMP directly using pip:

```bash
pip install .
```

This will create a `.emp` directory in your home directory and copy the default `hosts.json` file there. If you already have a `hosts.json` from a previous installation, it will not be overwritten.

## Usage

Once installed, you can run EMP using:

```bash
emp [command] [options]
```

### Basic Commands

1. Display help message with available commands:

    ```bash
    emp --help
    ```

2. Execute a command on a specific host:

    ```bash
    emp command HOSTNAME "ls -la"
    ```

3. Deploy a module to a specific host (attached mode):

    ```bash
    emp attached HOSTNAME ./path/to/module_directory
    ```
   This will deploy the module and show real-time output from the execution.

4. Deploy a module to a specific host (detached mode):

    ```bash
    emp detached HOSTNAME ./path/to/module_directory
    ```
   This will deploy the module using TMUX, allowing it to run in the background independently of your terminal session.

### Advanced Commands

5. Open an interactive TTY session with a host:

    ```bash
    emp tty HOSTNAME
    ```

6. Check the status of all connected hosts:

    ```bash
    emp check
    ```

## Configuration

The configuration files are located in your home directory's `.emp` folder, including:
- `hosts.json`: Define remote hosts and their connection details (hostname, port, username, password)
- Other module-specific configurations as needed

## Environment Variables

- V (int): Logging verbosity level (0=ERROR, 1=INFO, 2=DEBUG)
- RB (int): Rebuild flag (0 or 1)
- DT (int): Detached execution flag (0 or 1)

### Logging Levels

Control verbosity using the `V` environment variable:

```bash
# Default (show errors only)
V=0 emp attached HOSTNAME MODULE

# Standard level (info, warnings, errors)
V=1 emp detached HOSTNAME MODULE

# Detailed debugging output
V=2 emp check
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
emp tty HOSTNAME
```

## Key Features

- **Multi-host management**: Connect to and manage multiple remote devices
- **Parallel execution**: Run commands across all connected nodes simultaneously
- **Interactive access**: Open TTY sessions for direct command-line interaction
- **Module deployment**: Deploy Python modules to remote hosts with version tracking
- **Configuration flexibility**: Customize behavior through environment variables

## Development

The project is currently in version 0.1 and is actively being developed. Contributions and feedback are welcome!

## Todos

 - Implement sanity checks for modules (make sure that they have a run.sh file for example).
 - Refactor complex parts of the codebase like the large function that checks all nodes.
 - Implement tests somehow...

### License

This project is licensed under the MIT License - see the LICENSE file for details.