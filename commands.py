import json
from pprint import pprint
import paramiko
from termcolor import colored
from scp import SCPClient
from interactive import interactive_shell
import bash_commands

def createSSHClient(server, port, user, password, sock=None):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, password, sock=sock)
    return client

def command_checkall(session={}):
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
            host['scp'] = SCPClient(host['client'].get_transport())
        else:
            host['client'] = createSSHClient(host['ip'], host['port'], host['user'], host['password'])
            host['scp'] = SCPClient(host['client'].get_transport())
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
    try:
        chan = session['connections'][hostname]['client'].invoke_shell()
    except:
        raise Exception(f'Host "{hostname}" is unreachable')
    interactive_shell(chan)
    return session

def command_verbose(session):
    if session['verbose']:
        print('Verbose mode off')
        session['verbose'] = False
    else:
        print('Verbose mode on')
        session['verbose'] = True
    
    return session

def command_execall(command, session):
    verbose = session['verbose']
    if verbose: print(f'[*] Executing command "{command}" on all hosts')
    for hostname in session['connections']:
        host = session['connections'][hostname]
        if host['client'] is not None:
            stdin, stdout, stderr = host['client'].exec_command(command)
            if verbose: 
                print(f'### {hostname.upper()} ###')
                for line in stdout:
                    print(colored(line.strip('\n'), 'green'))
                for line in stderr:
                    print(colored(line.strip('\n'), 'red'))
    return session

def command_exec(hostname, command, session):
    verbose = session['verbose']
    # if verbose: print(f'[*] Executing command "{command}" on host {hostname}')
    host = session['connections'][hostname]
    if host['client'] is not None:
        stdin, stdout, stderr = host['client'].exec_command(command)
        if verbose: 
            print(f'### {hostname.upper()} ###')
            for line in stdout:
                print(colored(line.strip('\n'), 'green'))
            for line in stderr:
                print(colored(line.strip('\n'), 'red'))
    return session

def command_listcommands(session):
    print(f'Available commands: {", ".join([com for com in dir(bash_commands) if not com.startswith("__")])}')
    return session

def command_scan(hostname, session):
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
    host = session['connections'][hostname]
    command = f"""
        echo "Initing Scheduler"
        {host['paths']['conda']}/envs/dask/bin/dask-scheduler
        """
    session = command_exec(hostname, command, session)
    return session
    
def command_dask_start_worker(hostname, session):
    host = session['connections'][hostname]
    command = f"""
        echo "Initing Worker"
        {host['paths']['conda']}/envs/dask/bin/dask-worker {session['connections'][host['master_callsign']]['local_ip']}
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

