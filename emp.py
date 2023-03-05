import json
from pprint import pprint
import paramiko
from scp import SCPClient
from commands import Interface
from _version import __version__

art = """
  _____ __  __ ____  
 | ____|  \/  |  _ \ 
 |  _| | |\/| | |_) |
 | |___| |  | |  __/ 
 |_____|_|  |_|_|    v0.1                      
"""

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
import readline
import traceback
from termcolor import colored
import shlex

print(art)

#initializing CommandsClient object
interface = Interface()
input_session = PromptSession(history=FileHistory('.inp_history'))


while 1:
    try:
        line = input_session.prompt(f'(v{__version__})> ', auto_suggest=AutoSuggestFromHistory())
    except (KeyboardInterrupt, EOFError):
        print('\nbye!')
        break
    try:
        if line=='exit':
            break
        else:
            try:
                params = shlex.split(line)[1:]
                nodes = interface.hostname_parser(params[0])
                if nodes is not None:
                    if len(nodes) > 1:
                        getattr(interface, 'multipleNodeExecutionInterface')(nodes, 'command_'+line.split(' ')[0], *params[1:])
                    else:
                        getattr(interface, 'command_'+line.split(' ')[0])(*params)
                    #func(interface.hostname_parser(params[0]), *params[1:]) #*shlex.split(line)[1:])
            except IndexError:
                getattr(interface, 'command_'+line.split(' ')[0])()
            except Exception as e: print(e)
    except Exception:
        print(traceback.format_exc())