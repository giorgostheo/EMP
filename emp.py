import json
from pprint import pprint
import paramiko
from scp import SCPClient
from commands import Interface
from utilities import parse_file, parse_args
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
import argparse
import traceback
from termcolor import colored
import shlex
import sys
import os

print(art)

#initializing CommandsClient object
interface = Interface()
input_session = PromptSession(history=FileHistory('.inp_history'))

# Create the parser
parser = argparse.ArgumentParser()
parser.add_argument("-f", nargs='?', dest='file')
parser.add_argument("-i", nargs='?', dest='input')
args, unknown = parser.parse_known_args()

#executing commands if given as command line arguments
FILE = args.file
INPUT = args.input
if any([FILE,INPUT,unknown]):
    try:
        if not unknown:
            actions_dict = parse_file(FILE) if FILE else parse_args(INPUT)
            for action in actions_dict:
                try:
                    func = getattr(interface, 'command_'+action['command'])
                    print('\nExecuting {} {}'.format(action['command'], action['args']))
                    func(*shlex.shlex(action['args']))
                except Exception as e: print(e)
        else:
            print(f'Argument "{unknown[0]}" does not exist')
    except ValueError:
        print('Wrong format')
    except IOError:
        print(f'File {FILE} not found')
    except Exception as e:
        print(e)
    sys.exit()



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
                func = getattr(interface, 'command_'+line.split(' ')[0])
                func(*shlex.split(line)[1:])
            except Exception as e: print(e)
    except Exception:
        print(traceback.format_exc())