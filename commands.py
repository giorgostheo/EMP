import json, os
from pprint import pprint
import paramiko
from termcolor import colored
from scp import SCPClient
from interactive import interactive_shell
import sys
current_module = sys.modules[__name__]

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
            super(MySFTPClient, self).mkdir(path, mode)
        except IOError:
            if ignore_existing:
                pass
            else:
                raise

def createSSHClient(server, port, user, password, sock=None):
    '''
    Paramiko Connector
    '''
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, password, sock=sock)
    return client

def command_checkall(session={}):
    '''
    Checks if all nodes are up. Can also be used as the starting point for any new command that targets all nodes.
    TODO: Create a single interface that runs smth in all nodes.
    Ex. Instead of checkall, runall etc. create one func that take a command as input (check, run etc.) and runs on all nodes.
    '''
    verbose = session['verbose']

    if verbose: print('[+] Connecting to all hosts')

    if not session['connections']:
        hosts = json.load(open('hosts.json'))
    else:
        hosts = session['connections']

    for hostname in hosts:
        host = hosts[hostname]
        # try:
        if host['master_callsign']:
            transport = hosts[host['master_callsign']]['client'].get_transport()
            channel = transport.open_channel("direct-tcpip", (host['ip'], host['port']), (hosts[host['master_callsign']]['ip'], hosts[host['master_callsign']]['port']))
            host['client'] = createSSHClient(host['ip'], host['port'], host['user'], host['password'], sock=channel)
            host['sftp'] = MySFTPClient.from_transport(host['client'].get_transport())
        else:
            host['client'] = createSSHClient(host['ip'], host['port'], host['user'], host['password'])
            host['sftp'] = MySFTPClient.from_transport(host['client'].get_transport())
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
    
    session['connections'] = hosts
    return session

def command_tty(hostname, session):
    '''
    TTY for host - a terminal window for connecting and running commands. 
    TODO: Not sure if this is the optimal way to do this.
    '''
    try:
        chan = session['connections'][hostname]['client'].invoke_shell()
    except:
        raise Exception(f'Host "{hostname}" is unreachable')
    interactive_shell(chan)
    return session

def command_verbose(session):
    '''
    Changes global verbosity
    '''
    if session['verbose']:
        print('Verbose mode off')
        session['verbose'] = False
    else:
        print('Verbose mode on')
        session['verbose'] = True
    
    return session

def command_execall(command, session):
    '''
    Same as exec, but for all nodes
    '''
    verbose = session['verbose']
    if verbose: print(f'[*] Executing command "{command}" on all hosts')
    for hostname in session['connections']:
        session = command_exec(hostname, command, session)
    return session

def command_exec(hostname, command, session):
    '''
    Exec a single command on a specific node.
    '''
    verbose = session['verbose']
    # if verbose: print(f'[*] Executing command "{command}" on host {hostname}')
    host = session['connections'][hostname]
    if host['client'] is not None:
        stdin, stdout, stderr = host['client'].exec_command(command)
        if verbose: 
            for line in stdout:
                print(colored(f"[{hostname}] "+line.strip('\n'), 'green'))
            for line in stderr:
                print(colored(f"[{hostname}] "+line.strip('\n'), 'red'))
    return session

def command_ls(session):
    '''
    This lists all commands that are available (locally - this doesnt affect nodes)
    '''
    [print(com.removeprefix("command_")) for com in dir(current_module) if com.startswith("command")]
    return session

def command_deploy_module(hostname, module, session):
    '''
    This is used to deploy a module.
    Input:
        hostname - host callsign (alpha, bravo etc.)
        module - module name (directory in modules folder)
        session - the paramiko session
    
    What is done:
        1) Create directories ("modules" and subdir for specific module with name)
        2) Clone local module dir to remote dir with the same name
        3) run init.sh file - This needs to be present in the module directory. For python modules,
        it should create the module's environment and install requirements.
    '''
        
    sftp = session['connections'][hostname]['sftp']
    sftp.mkdir(f'modules', ignore_existing=True)
    sftp.mkdir(f'modules/{module}', ignore_existing=True)
    sftp.put_dir(f'modules/{module}', f'modules/{module}')

    command_exec(hostname, f'cd modules/{module}; bash init.sh', session)

    return session

def command_exec_module(hostname, module, session):
    '''
    This runs an already deployed module (i.e. executes the run.sh file that needs to be present in the module dir)
    '''
    command_exec(hostname, f'cd modules/{module}; bash run.sh', session)

    return session

def command_scan(hostname, session):
    '''OLD
    Check LAN of node to see if you can find other nodes.
    '''
    command_string = """
        if ! command -v nmap &> /dev/null
        then
            echo "Installing nmap..."
            sudo apt install nmap
        fi
        nmap -n -sn 192.168.0.0/24 -oG - | awk '/Up$/{print $2}'
    """
    host = session['connections'][hostname]
    if host['client'] is not None:
        stdin, stdout, stderr = host['client'].exec_command(command_string)
        for line in [ln.strip('\n') for ln in stdout]:
            try: 
                idx = [session['connections'][hostname]['local_ip'] for hostname in session['connections']].index(line.strip('\n'))
                print(colored(f"{line} - {list(session['connections'].keys())[idx]}", 'green'))
            except:
                print(colored(line, 'yellow'))
            # print(colored(line.strip('\n'), 'green'))
        for line in stderr:
            print(colored(line.strip('\n'), 'red'))
    return session

def command_dask_start_master(hostname, session):
    '''OLD
    Init Dask scheduler
    '''
    host = session['connections'][hostname]
    command = f"""
        echo "Initing Scheduler"
        {host['paths']['conda']}/envs/dask/bin/dask-scheduler
        """
    session = command_exec(hostname, command, session)
    return session
    
def command_dask_start_worker(hostname, session):
    '''OLD
    Init Dask worker
    '''
    host = session['connections'][hostname]
    command = f"""
        echo "Initing Worker"
        {host['paths']['conda']}/envs/dask/bin/dask-worker tcp://{session['connections'][host['master_callsign']]['local_ip']}:8786
        """
    session = command_exec(hostname, command, session)
    return session

def command_install_conda_dask(hostname, session):
    '''OLD
    Install dask
    '''
    host = session['connections'][hostname]
    command = f"""
    CONDA_DIR="{host['paths']['conda']}"

    # add other packages here alongside htop
    apt-get install -y htop

    if [ ! -d $CONDA_DIR ] 
    then
    echo "Conda does not exist. Creating..." 
    # change this for newer conda versions
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh;
    bash Miniconda3-latest-Linux-x86_64.sh -b
    # if you extend this to support ymls, change the following command 
    $CONDA_DIR/bin/conda create -y -n dask python=3.9
    $CONDA_DIR/bin/conda install -n dask -y -c conda-forge dask distributed scikit-learn scipy numpy pandas geopandas dask-geopandas
    else
    echo "Conda exists"
    fi
    """
    session = command_exec(hostname, command, session)
    return session
    

# ssh = createSSHClient(config['alpha']['host'], config['alpha']['port'], config['alpha']['uname'], config['alpha']['pass'])
# scp = SCPClient(ssh.get_transport())
# scp.put('script.sh', f"{config['alpha']['paths']['user']}/config.json")
# stdin, stdout, stderr = ssh.exec_command('sudo -S bash script.sh',  get_pty=True)
# stdin.write(config['alpha']['pass'] + "\n")
# # stdin, stdout, stderr = ssh.exec_command('ls')
# stdin.flush()

# print(stdout.read())
# print(stderr.read())

