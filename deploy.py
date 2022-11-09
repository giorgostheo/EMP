import json
from pprint import pprint
import paramiko
from scp import SCPClient
import commands

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


session=commands.command_checkall(
    {'curent_host':'localhost', 
    'verbose': True, 
    'connections': {}}
)
input_session = PromptSession(history=FileHistory('.inp_history'))


while 1:
    try:
        line = input_session.prompt(f'({session["curent_host"]})> ', auto_suggest=AutoSuggestFromHistory())
    except (KeyboardInterrupt, EOFError):
        print('\nbye!')
        break
    try:
        if line=='exit':
            break
        else:
            try:
                func = getattr(commands, 'command_'+line.split(' ')[0])
                session = func(*shlex.split(line)[1:], session=session) 
            except Exception as e: print(e)
    except Exception:
        print(traceback.format_exc())