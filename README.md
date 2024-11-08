# EMP

Edge Management Platform - Create and deploy modules to the edge.

## Usage

```Shell
python emp.py
```

### Tips
- Use "ls" command to list all the available commands.
- All commands are part of the commands.py file. All commands that are available in the CLI should start with "command_" (they are automatically detected, that is why this is needed)
- Connection object is passed to each one and returned by each one. This is bad as it should be a class...
- ...

### Roadmap

- Port over data broker from Emeralds org and make it a built-in module
- Add p2p VPN as a built-in module that can be deployed between multiple nodes
- Add support for deploy over multiple nodes at the same time
- Add complex deployments in the form of "plan" files that can replicate workflows like pipelines across multiple devices
- Replace current data broker with websockets

See issues
