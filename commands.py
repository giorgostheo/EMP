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
import threading
from threading import Lock
from copy import copy
import time
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


    def __init__(self, host='', connections={}, verbose=True):
        '''
        Initialize parameters, execute init commands
        '''
        self.connections = connections
        self.verbose = verbose
        self.command_checkall(host)

    def parse_hostname(self, hostname):
        hosts = json.load(open('/Users/georgetheodoropoulos/Code/emeralds/EMP/hosts.json'))

        if hostname in hosts.keys():
            return {hostname:hosts[hostname]}
        else:
            group = [name for name in hosts.keys() if name.startswith(hostname)]
            print(group)
            if group:
                return {name:hosts[name] for name in group}
            else:
                return hosts


    def createSSHClient(self,server, port, user, password, sock=None, timeout=10):
        '''
        Paramiko Connector
        '''
        client = paramiko.SSHClient()
        # client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server, port, user, password=password, sock=sock, timeout=timeout, key_filename="/Users/georgetheodoropoulos/.ssh/id_rsa.pub")
        return client
    
    def command_checkall(self, host, verbose=False):
        """
        Establish SSH connections to all hosts in parallel, respecting dependencies.
        """
        verbose = self.verbose

        hosts = self.parse_hostname(host)

        if verbose: 
            print(f'[+] Connecting to {hosts.keys()}')

        lock = Lock()
        threads = []

        # Initialize threading.Event for each host
        for hostname in hosts:
            hosts[hostname]['event'] = threading.Event()

        # Start a thread for each host
        for hostname in hosts:
            thread = threading.Thread(
                target=self.connect_host,
                args=(hostname, hosts, lock)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to finish
        for thread in threads:
            thread.join()

        # After all threads are done, set the connections
        self.connections = hosts

        # Print connection status if verbose
        # if verbose:
        #     for hostname in hosts:
        #         host = hosts[hostname]
        #         if host['client'] is None:
        #             print(colored(hostname, 'red'), end=" ")
        #         else:
        #             print(colored(hostname, 'green'), end=" ")
        #     print()

    def connect_host(self, hostname, hosts_dict, lock):
        """
        Threaded function to connect a single host.
        """
        host = hosts_dict[hostname]
        event = host['event']

        try:
            # If this host depends on a master, wait for it to connect first
            if host.get('master_callsign'):
                master_callsign = host['master_callsign']
                master_host = hosts_dict[master_callsign]
                master_event = master_host['event']

                # Wait for master to finish connecting
                master_event.wait(timeout=15)  # Wait up to 10 seconds

                # Check if the master client is available
                with lock:
                    if master_host.get('client') is None:
                        # Master failed, so this host can't connect
                        host['client'] = None
                        host['sftp'] = None
                        event.set()
                        return

                    # Use the master's transport to connect to this host
                    transport = master_host['client'].get_transport()
                    channel = transport.open_channel(
                        "direct-tcpip",
                        (host['ip'], host['port']),
                        (master_host['ip'], master_host['port'])
                    )

                    # Create SSH client through the channel
                    client = self.createSSHClient(
                        host['ip'], host['port'],
                        host['user'], host['password'],
                        sock=channel,
                        timeout=5
                    )



            else:
                # Direct connection
                client = self.createSSHClient(
                    host['ip'], host['port'],
                    host['user'], host['password'],
                    timeout=5
                )

            # Create SFTP client
            sftp = self.MySFTPClient.from_transport(client.get_transport())

            stdin, stdout, stderr = client.exec_command('tmux ls')
            stderr = stderr.readlines()
            print(stderr)

            if stderr and stderr[0].startswith('no server running'):
                print(colored(f"[{hostname}] Available, Free", 'green'))
            else:
                jobs = [val.split(':')[0] for val in stdout.readlines()]
                print(colored(f"[{hostname}] Available, Busy running: {jobs}", 'yellow'))
            # Save to hosts dictionary (with lock)
            with lock:
                host['client'] = client
                host['sftp'] = sftp

        except Exception as error:
            # Log error or handle it
            with lock:
                host['client'] = None
                host['sftp'] = None
                print(colored(f"[{hostname}] Unavailable due to error {error}", 'red'))

        finally:
            # Signal this host thread is done
            event.set()

    def command_checkall_old(self, host):
        '''
        Checks if all nodes are up. Can also be used as the starting point for any new command that targets all nodes.
        TODO: Create a single interface that runs smth in all nodes.
        Ex. Instead of checkall, runall etc. create one func that take a command as input (check, run etc.) and runs on all nodes.
        '''
        verbose = self.verbose

        if verbose: 
            if host=='':
                print('[+] Connecting to all hosts')
            else:
                print(f'[+] Connecting to {host}')

        if not self.connections:
            hosts = json.load(open('/Users/georgetheodoropoulos/Code/emeralds/EMP/hosts.json'))
        else:
            hosts = self.connections

        if host!='':
            hosts = {host:hosts[host]}

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

    def command_monitorall(self):
        '''
        Same as exec, but for all nodes
        '''
        verbose = self.verbose
        if verbose: print(f'[*] Executing command "tmux ls" on all hosts')
        for hostname in self.connections:
            host = self.connections[hostname]
            if host['client'] is not None:
                stdin, stdout, stderr = host['client'].exec_command('tmux ls')
                stderr = stderr.readlines()

                if stderr and stderr[0].startswith('no server running'):
                    print(colored(f"[{hostname}] No tmux server running", 'green'))
                else:
                    jobs = [val.split(':')[0] for val in stdout.readlines()]
                    print(colored(f"[{hostname}] Busy running: {jobs}", 'yellow'))
                # print(stdout.readlines())
                # print(stderr.readlines())
                # if verbose: 
                #     for line in stdout:
                #         print(colored(f"[{hostname}] "+line.strip('\n'), 'green'))
                #     for line in stderr:
                #         print(colored(f"[{hostname}] "+line.strip('\n'), 'red'))

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

    def command_module_exec_tmux(self, hostname, module):
        '''
        This runs an already deployed module (i.e. executes the run.sh file that needs to be present in the module dir)
        '''
        self.command_exec(hostname, f'tmux new-session -d -s _emp_{module}_{int(time.time())} "cd modules/{module}; bash run.sh"')
        # pid = int(stdout.readline())
        # print("PID", pid)

    def command_module_exec_nh(self, hostname, module):
        '''
        This runs an already deployed module (i.e. executes the run.sh file that needs to be present in the module dir)
        '''
        client = self.connections[hostname]['client']
        transport = client.get_transport()
        channel = transport.open_session()
        # filename = f"res.txt"
        log_file = f'modules/{module}/logfile'
        channel.exec_command(f'cd modules/{module}; touch mylock_$$; bash run.sh > /dev/null 2>&1; rm mylock_$$\n') # WORKS
        # pid = int(stdout.readline()) modules/{module}/{filename}
        # print("PID", pid)

    def command_module_old(self, hostname, module, rebuild, detach):
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
            self.command_module_exec_tmux(hostname, module)
        else:
            if verbose:
                print(f'\n-Running {module} in stdout mode..')
            self.command_module_exec(hostname, module)

    def command_module(self, module, rebuild, detach):
        '''
        Responsible for syncing, deploying and executing a module.
        If a module already exists, validations or actions are being performed.
        E.g update enviroment/update files
        '''
        # print(self.connections)
        for hostname in self.connections:
            self.command_module_old(hostname, module, rebuild, detach)

    def command_module_par(self, module, rebuild, detach):
        '''
        Responsible for syncing, deploying and executing a module.
        If a module already exists, validations or actions are being performed.
        E.g update enviroment/update files
        '''
        verbose = self.verbose

        threads = []

        # Start a thread for each host
        for hostname in self.connections:
            thread = threading.Thread(
                target=self.command_module_old,
                args=(hostname, module, rebuild, detach)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        

    # ssh = createSSHClient(config['alpha']['host'], config['alpha']['port'], config['alpha']['uname'], config['alpha']['pass'])
    # scp = SCPClient(ssh.get_transport())
    # scp.put('script.sh', f"{config['alpha']['paths']['user']}/config.json")
    # stdin, stdout, stderr = ssh.exec_command('sudo -S bash script.sh',  get_pty=True)
    # stdin.write(config['alpha']['pass'] + "\n")
    # # stdin, stdout, stderr = ssh.exec_command('ls')
    # stdin.flush()

    # print(stdout.read())
    # print(stderr.read())

