import time
import json, os
import re
from pprint import pprint
import paramiko
from termcolor import colored
from scp import SCPClient
from interactive import interactive_shell
from utilities import VersionControl
import sys
from copy import copy
current_module = sys.modules[__name__]


class Interface():
    '''
    Class implementaton for all available commands
    '''
    
    class MySFTPClient(paramiko.SFTPClient):
        '''
        This is here to allow the sftp connection to clone the modules. Not the most elegant solution.
        TODO: Add this to a new file and make it the primary connection interface (not only sftp for ex.)
        '''
        def put_dir(self, source, target):
            ''' Uploads the contents of the source directory to the target path. The
                target directory needs to exists. All subdirectories in source are 
                created under target.
            '''
            for item in os.listdir(source):
                if os.path.isfile(os.path.join(source, item)):
                    self.put(os.path.join(source, item), '%s/%s' % (target, item))
                else:
                    self.mkdir('%s/%s' % (target, item), ignore_existing=True)
                    self.put_dir(os.path.join(source, item), '%s/%s' % (target, item))

        def mkdir(self, path, mode=511, ignore_existing=False):
            ''' Augments mkdir by adding an option to not fail if the folder exists  '''
            try:
                super(__class__, self).mkdir(path, mode)
            except IOError:
                if ignore_existing:
                    pass
                else:
                    raise


    def __init__(self, connections={}, verbose=True):
        '''
        Initialize parameters, execute init commands
        '''
        self.connections = connections
        self.verbose = verbose
        self.command_checkall()

    def createSSHClient(self,server, port, user, password, sock=None, timeout=10):
        '''
        Paramiko Connector
        '''
        client = paramiko.SSHClient()
        # client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server, port, user, password=password, sock=sock, timeout=timeout, key_filename="/Users/georgetheodoropoulos/.ssh/id_rsa.pub")
        return client

    def command_checkall(self):
        '''
        Checks if all nodes are up. Can also be used as the starting point for any new command that targets all nodes.
        TODO: Create a single interface that runs smth in all nodes.
        Ex. Instead of checkall, runall etc. create one func that take a command as input (check, run etc.) and runs on all nodes.
        '''
        verbose = self.verbose

        if verbose: print('[+] Connecting to all hosts')

        if not self.connections:
            hosts = json.load(open('/Users/georgetheodoropoulos/Code/EMP/hosts.json'))
        else:
            hosts = self.connections

        for hostname in hosts:
            host = hosts[hostname]
            # try:
            if host['master_callsign']:
                transport = hosts[host['master_callsign']]['client'].get_transport()
                channel = transport.open_channel("direct-tcpip", (host['ip'], host['port']), (hosts[host['master_callsign']]['ip'], hosts[host['master_callsign']]['port']))
                try:
                    host['client'] = self.createSSHClient(host['ip'], host['port'], host['user'], host['password'], sock=channel, timeout=5)
                    host['sftp'] = self.MySFTPClient.from_transport(host['client'].get_transport())
                except Exception as error:
                    # handle the exception
                    print("An exception occurred:", error)
                    host['client'] = None
                    host['sftp'] = None
            else:
                try:
                    host['client'] = self.createSSHClient(host['ip'], host['port'], host['user'], host['password'], timeout=5)
                    host['sftp'] = self.MySFTPClient.from_transport(host['client'].get_transport())
                except Exception as error:
                    # handle the exception
                    print("An exception occurred:", error)
                    host['client'] = None
                    host['sftp'] = None
            # except:
            #     host['client'] = None
            #     host['scp'] = None
                # print(f'Could not connect to {host["name"]}')
        if verbose:
            for hostname in hosts:
                if hosts[hostname]['client'] is None:
                    print(colored(hostname, 'red'), end= " ")
                else:
                    print(colored(hostname, 'green'), end= " ")
            print()
        
        self.connections = hosts

    def command_tty(self, hostname):
        '''
        TTY for host - a terminal window for connecting and running commands. 
        TODO: Not sure if this is the optimal way to do this.
        '''
        try:
            chan = self.connections[hostname]['client'].invoke_shell()
        except:
            raise Exception(f'Host "{hostname}" is unreachable')
        interactive_shell(chan)

    def command_verbose(self):
        '''
        Changes global verbosity
        '''
        if self.verbose:
            print('Verbose mode off')
            self.verbose = False
        else:
            print('Verbose mode on')
            self.verbose = True

    def command_execall(self, command):
        '''
        Same as exec, but for all nodes
        '''
        verbose = self.verbose
        if verbose: print(f'[*] Executing command "{command}" on all hosts')
        for hostname in self.connections:
            self.command_exec(hostname, command)

    def command_exec(self, hostname, command):
        '''
        Exec a single command on a specific node.
        '''
        verbose = self.verbose
        # if verbose: print(f'[*] Executing command "{command}" on host {hostname}')
        host = self.connections[hostname]
        if host['client'] is not None:
            stdin, stdout, stderr = host['client'].exec_command(command, get_pty=True)
            if verbose: 
                for line in stdout:
                    print(colored(f"[{hostname}] "+line.strip('\n'), 'green'))
                for line in stderr:
                    print(colored(f"[{hostname}] "+line.strip('\n'), 'red'))

    def command_ls(self):
        '''
        This lists all commands that are available (locally - this doesnt affect nodes)
        '''
        [print(com.removeprefix("command_")) for com in dir(self.__class__) if com.startswith("command")]


    def command_sync(self, hostname, module):
        '''
        This is used to deploy a module.
        Input:
            hostname - host callsign (alpha, bravo etc.)
            module - module name (directory in modules folder)
            session - the paramiko session
        
        What is done:
            1) Create directories ("modules" and subdir for specific module with name)
            2) Clone local module dir to remote dir with the same name
        '''
        sftp = self.connections[hostname]['sftp']

        sftp.mkdir('modules', ignore_existing=True)
        sftp.mkdir(f'modules/{module}', ignore_existing=True)

        should_rebuild = False
        verbose = self.verbose
        client = copy(sftp)
        client.chdir('modules')

        # Check if any changes have been made to the module
        client.chdir(module)
        source_dir = os.path.abspath(f'.')
        vc = VersionControl(client, source_dir, verbose)
        vc.compare_modules()
        vc.update_target()
        should_rebuild = vc.should_rebuild

        return should_rebuild

    def command_module_deploy(self, hostname, module):
        '''
        Builds the given module(runs requirements file)
        '''
        if 'init.sh' in os.listdir(f'.'):
            print('\n-Found init script..')
            self.command_exec(hostname, f'cd modules/{module}; bash init.sh')

    def command_module_exec(self, hostname, module):
        '''
        This runs an already deployed module (i.e. executes the run.sh file that needs to be present in the module dir)
        '''
        self.command_exec(hostname, f'cd modules/{module}; bash run.sh')
        # pid = int(stdout.readline())
        # print("PID", pid)

    def command_module_exec_nh(self, hostname, module):
        '''
        This runs an already deployed module (i.e. executes the run.sh file that needs to be present in the module dir)
        '''
        client = self.connections[hostname]['client']
        transport = client.get_transport()
        channel = transport.open_session()
        filename = f"result_module_{module}_{int(time.time())}.txt"
        # filename = f"res.txt"
        channel.exec_command(f'cd modules/{module}; bash run.sh > {filename}')
        print(f'OUTPUT FILENAME: {filename}')
        # pid = int(stdout.readline())
        # print("PID", pid)

    def command_module(self, hostname, module, rebuild, detach):
        '''
        Responsible for syncing, deploying and executing a module.
        If a module already exists, validations or actions are being performed.
        E.g update enviroment/update files
        '''
        verbose = self.verbose

        # SYNC
        if verbose:
            print('\n-Syncing  module..')
        should_build = self.command_sync(hostname, module)

        # DEPLOY
        if should_build or rebuild:
            if verbose:
                print('\n-Building  module..')
            self.command_module_deploy(hostname, module)

        # EXEC
        if detach:
            if verbose:
                print(f'\n-Running {module} in detached mode..')
            self.command_module_exec_nh(hostname, module)
        else:
            if verbose:
                print(f'\n-Running {module} in stdout mode..')
            self.command_module_exec(hostname, module)


        

    # ssh = createSSHClient(config['alpha']['host'], config['alpha']['port'], config['alpha']['uname'], config['alpha']['pass'])
    # scp = SCPClient(ssh.get_transport())
    # scp.put('script.sh', f"{config['alpha']['paths']['user']}/config.json")
    # stdin, stdout, stderr = ssh.exec_command('sudo -S bash script.sh',  get_pty=True)
    # stdin.write(config['alpha']['pass'] + "\n")
    # # stdin, stdout, stderr = ssh.exec_command('ls')
    # stdin.flush()

    # print(stdout.read())
    # print(stderr.read())

