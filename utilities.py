from pathlib import Path

def parse_args(target:list) ->  list:
    """
    Parses the arguments and returns a dict of commands and args
    """
    """TODO: Can an argument have only one command?"""
    commands = []
    processes = target.split(';')
    for i, process in enumerate(processes):
        command_args = process.strip().split(' ',1)
        command = command_args.pop(0)
        args = '' if not command_args else command_args[0].strip()
        commands.append(
            {
                'order':i+1,
                'command':command,
                'args':args
            })
    return commands

def parse_file(path:str) -> list:
    """
    Parses commands from file
    """
    with open(Path(path)) as f:
        lines = [line.rstrip() for line in f]
    commands = ';'.join(lines)
    return parse_args(commands)


    