
import threading
import os
import time
import logging
import subprocess
from datetime import datetime


###################################################################################
###                            CONFIGURATION SETTINGS                           ###
###                      Change the following before you run                    ###
###################################################################################

# You need two machines to run this experiment.
# Provide SSH connection details to allow the CLIENT to launch processes on the SERVER via SSH.
CLIENT = ''     # IP address or hostname of the client machine
SERVER = ''     # IP address or hostname of the server machine
USERNAME = ''   # Your username for both machines

CLIENT_HOSTNAME = 'birch.sysnet.ucsd.edu' # Hostname of the client machine  
CLIENT_IP =  '169.228.66.113'       # IP address of the client machine  
# These two values are used for synchronization between different client runtimes (i.e., load generators).  
# Since we have multiple request types, multiple client runtimes are needed.  
# The client runtime matching the hostname acts as the leader, while others are followers.  
# The leader and followers synchronize as a barrier to ensure they start sending requests at the same time.  

CLIENT_NUMANODE = 1  # NUMA node assigned for the client runtime (load generator) on the client machine.  
SERVER_NUMANODE = 1  # NUMA node assigned for running the BadgerDB server on the server machine.  

# The load generator uses directpath mode, so you need to provide the PCI address of the NIC.
# DirectPath allows client runtime send and receive packets directly from the NIC,
# achieving better performance compared to when the IOKernel handles all packets.
NIC_PCI = '0000:b5:00.1'  
# You can typically find the NIC PCI address using: 
#   lspci | grep -i 'ethernet'
# Regardless of whether DirectPath is enabled, you need to modify the hardcoded NIC port
# in the source file: iokernel/dpdk.c:283 (`dp.port = 1;`).
# The port is typically either 0 or 1.

# Bind your server machine's Ethernet port to this IP address.  
# This IP address will be used for BadgerDB server.
# Example: sudo ifconfig enp181s0f1np1 192.168.1.2  
# Client runtimes will use IP addresses in the range 192.168.1.{3,4,...}.  
BADGERDB_SERVER_IP = '192.168.1.2'

# Path to the BadgerDB dataset.
# Download the dataset from:
# https://drive.google.com/file/d/1umPzzNkfNgkitHGt_wl-5t2stFBN6o4w/view?usp=share_link
# After downloading, extract it using:
# tar -xzvf db_data.tar.gz
# Ensure the extracted data is placed at the following path:
DATASET_PATH = "/data/preempt/go/db_data"

#################################################################################
###                           END OF CONFIGURATION                            ###
#################################################################################

# The configuration of client runtimes (load generator)
CLIENT_NETPFX = "192.168.1"
CLIENT_NETMASK = '255.255.255.0'
CLIENT_GATEWAY = '192.168.1.0'

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__)) 
SCRIPT_PATH = os.path.dirname(SCRIPT_PATH) # Script path
EXP_PATH = os.path.dirname(SCRIPT_PATH)    # Experiment path
CLIENT_PATH = os.path.dirname(EXP_PATH)    # Project home path
# The results and logs will appear in `experiments/result/fig7`. 

# This assumes the server and client clone the Aspen repository into the same directory 
SERVER_PATH = CLIENT_PATH  
SERVER_PATH = os.path.join(SERVER_PATH, 'aspen-go/badger-bench/server')  
# The rocksdb-server log will be in 'aspen-go/badger-bench/server/server_log' in server.
SERVER_BINARY = 'badger-server'  

LOGGER = logging.getLogger('experiment')
logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.DEBUG)


def IP(x):
    assert x >= 3 and x < 15  # we can only use IP from 192.168.1.3
    return "{}.{}".format(CLIENT_NETPFX, x)

def alloc_ip(experiment):
    ip = IP(experiment['nextip'])
    experiment['nextip'] += 1
    return ip


FUNCTION_REGISTRY = {}

def register_fn(name, fn):
  global FUNCTION_REGISTRY
  FUNCTION_REGISTRY[name] = fn

def sleep_5():
    runcmd("sleep 5")

register_fn('sleep_5', sleep_5)

LOGGER = logging.getLogger('experiment')
logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.DEBUG)

def _reset_log():
    import sys
    for handler in LOGGER.handlers[:]: LOGGER.removeHandler(handler)
    sh = logging.StreamHandler(sys.stdout)
    LOGGER.addHandler(sh)

def INITLOGGING(exp):
    _reset_log()
    _hostname = subprocess.check_output("hostname -s", shell=True).strip().decode('utf-8')
    fh = logging.FileHandler('{}/pylog.{}.log'.format(exp['path'], _hostname))
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    LOGGER.addHandler(fh)

def validate_machine_info():
    """ Validates that the required machine info is valid and verifies SSH and sudo access. """

    variables = {
        'CLIENT': CLIENT,
        'SERVER': SERVER,
        'USERNAME': USERNAME
    }
    # Validate that all variables are non-empty strings
    for name, value in variables.items():
        if not isinstance(value, str) or not value.strip():
            print(f"Error: {name} is empty or not a valid string.")
            return False

    # Command to verify hostnames and username.
    cmdstr = 'ssh -tt {}@{} \'{}\''.format(USERNAME, SERVER, 'whoami')
    try:
        _ = _runcmd(cmdstr, True)
    except subprocess.CalledProcessError as e:
        print(f"SSH process failed: {e}")
        return False
    
    print("SSH and sudo verification successful.")
    return True


class ThreadManager:
    def __init__(self):
        self.procs = {}
        self.remote_procs = {}
        self.proclock = threading.Lock()
        self.event = threading.Event()
        self.clientgo = threading.Event()

    def append_proc(self, proc):
        with self.proclock:
          self.procs[proc.pid] = proc

    def append_remote_proc(self, proc):
        with self.proclock:
          self.remote_procs[proc.pid] = proc

    def join_all_proc(self):
        procs = list(self.procs.values())
        print('join all procs:', procs)
        for p in procs:
            p.wait()

    def kill_all_remote_proc(self):
        for p in self.remote_procs.values():
            p.kill()
    
    def __new_thread(self, target, args):
        try:
            target(*args)
        except Exception as e:
            LOGGER.exception("Thread threw exception: %s", str(e))
            self.complete()

    def new_thread(self, target, args):
        t = threading.Thread(
            target=ThreadManager.__new_thread, args=(self, target, args))
        t.daemon = True
        t.start()

def runcmd(*args, **kwargs):
    assert 'outp' not in kwargs
    assert len(args) == 1
    return _runcmd(args[0], True, **kwargs)

def _runcmd(cmdstr, outp, suppress=False, **kwargs):
    kwargs['executable'] = kwargs.get("executable", "/bin/bash")
    kwargs['cwd'] = kwargs.get('cwd', "./")
    if outp:
        LOGGER.debug("running {%s}: " % cmdstr)
        res = subprocess.check_output(cmdstr, shell=True, **kwargs)
        return res
    else:
        p = subprocess.Popen(cmdstr, shell=True,
                             stdin=subprocess.PIPE, **kwargs)
        LOGGER.info("[%04d]: launched {%s}" % (p.pid, cmdstr))
        return p

def launch(*args, **kwargs):
    assert 'outp' not in kwargs
    assert len(args) == 1
    return _runcmd(args[0], False, **kwargs)


def new_experiment(go_variant, procs, preempt_mechanism, preempt_quantum_us, asyncpreemptoff, syncpreemptoff):
    name = "run.{}-{}-{}-{}-{}".format(datetime.now().strftime('%Y%m%d%H%M%S'), 
                                       go_variant, procs, preempt_mechanism, preempt_quantum_us)

    if asyncpreemptoff:
        name += "-asyncpreemptoff"
    if syncpreemptoff:
        name += "-syncpreemptoff"

    x = {
        'name': name,
        'nextip': 3,
        'hosts': {CLIENT: {}, SERVER: None}
    }
    return x

def add_server_app(experiment, procs=8, preempt_mechanism='signal', preempt_quantum_us=10000, sysmon_freqpoll=False, asyncpreemptoff=False, syncpreemptoff=False, protocol='http', preempt_info=1,  **kwargs):
    server = {
        'name': kwargs.get('name', 'go-server'),
        'binary': os.path.join(SERVER_PATH, SERVER_BINARY),
        'dataset': DATASET_PATH,
        'ip': BADGERDB_SERVER_IP,
        'numanode': SERVER_NUMANODE,
        'port': 5000,
        'procs': procs,
        'UINTR': 1 if preempt_mechanism == 'uintr' else 0,
        'preempt_info': preempt_info,
        'preempt_quantum': preempt_quantum_us * 1000,
        'sysmon_freqpoll': sysmon_freqpoll,
        'asyncpreemptoff': asyncpreemptoff,
        'syncpreemptoff': syncpreemptoff,
        'outpath': os.path.join(os.path.join(SERVER_PATH, 'server_log'), experiment['name']),
    }
    experiment['hosts'][SERVER] = server
    return server

def add_client_apps(experiment, server_handle, directpath=False, protocol='http', short_percent=0.99, mpps=1, start_mpps=0, samples=10, runtime=20, **kwargs):
    apps = []

    # Client runtime sending short requests.
    kthreads, uthreads = 20, 40
    x = {
        'name': 'short_client',
        'binary': os.path.join(CLIENT_PATH, 'apps/loadgen-go/target/release/synthetic') +' --config',
        'custom_conf': ['enable_directpath 1'],
        'host_addr': alloc_ip(experiment),
        'host_netmask': CLIENT_NETMASK,
        'host_gateway': CLIENT_GATEWAY,
        'runtime_kthreads': kthreads,
        'runtime_spinning_kthreads': kthreads,
        'runtime_guaranteed_kthreads': kthreads,
        'uthreads': uthreads,
        'serverip': server_handle['ip'],
        'serverport': server_handle['port'],
        'mpps': mpps * short_percent,
        'start_mpps': start_mpps * short_percent,
        'samples': samples,
        'runtime': runtime,
        'protocol': 'http',
        'transport': 'tcp',
        'http_uri': '/getkey/1',
        'path': os.path.join(experiment['path'], 'short'), 
        'args': "{serverip}:{serverport} --mode runtime-client --protocol {protocol} --transport {transport} --http_uri {http_uri} --threads {uthreads} --mpps={mpps} --start_mpps {start_mpps} --samples={samples} --runtime={runtime} --barrier-peers {npeers} --barrier-leader {leader}"
    }
    apps.append(x)

    # Client runtime sending long requests.
    kthreads, uthreads = 6, 40
    x = {
        'name': 'long_client',
        'binary': os.path.join(CLIENT_PATH, 'apps/loadgen-go/target/release/synthetic') +' --config',
        'custom_conf': ['enable_directpath 1'],
        'host_addr': alloc_ip(experiment),
        'host_netmask': CLIENT_NETMASK,
        'host_gateway': CLIENT_GATEWAY,
            'runtime_kthreads': kthreads,
        'runtime_spinning_kthreads': kthreads,
        'runtime_guaranteed_kthreads': kthreads,
        'uthreads': uthreads,
        'serverip': server_handle['ip'],
        'serverport': server_handle['port'],
        'mpps': mpps * (1 - short_percent),
        'start_mpps': start_mpps * (1 - short_percent),
        'samples': samples,
        'runtime': runtime,
        'protocol': 'http',
        'transport': 'tcp',
        'http_uri': '/iteratekey/3600/1',
        'path': os.path.join(experiment['path'], 'long'), 
        'args': "{serverip}:{serverport} --mode runtime-client --protocol {protocol} --transport {transport} --http_uri {http_uri} --threads {uthreads} --mpps={mpps} --start_mpps {start_mpps} --samples={samples} --runtime={runtime} --barrier-peers {npeers} --barrier-leader {leader}"
    }
    apps.append(x)

    iokernel = {
        'binary': os.path.join(CLIENT_PATH, 'iokerneld'),
        'scheduler': 'simple',
        'options': f'nobw noht numanode {CLIENT_NUMANODE}'
    }
    if directpath:
        iokernel['options'] += f" nicpci {NIC_PCI}"
    
    experiment['hosts'][CLIENT] = {
        'apps': apps,
        'iokernel': iokernel,       
    }

    return apps

def finalize_client_cohort(client_apps):
    for i, cfg in enumerate(client_apps):
        cfg['npeers'] = len(client_apps)
        if i == 0:
            cfg['leader'] = CLIENT_HOSTNAME
        else:
            cfg['leader'] = CLIENT_IP
            cfg['before'] = cfg.get('before', []) + ['sleep_5']

def launch_iokerneld(experiment):
    cfg = experiment['hosts'][CLIENT].get('iokernel', {})
    binary = cfg.get('binary', './iokerneld')
    scheduler = cfg.get('scheduler', 'simple')
    options = cfg.get('options', 'nobw')
    logpath = os.path.join(experiment['path'], 'iokernel.log')
    proc = launch("sudo {} {} {} 2>&1 | ts %s > {}".format(
        binary, scheduler, options, logpath))
    for i in range(10):
        time.sleep(1)
        if os.system("grep -q 'running dataplane' {}".format(logpath)) == 0:
            break
        proc.poll()
        if proc.returncode is not None:
            break

    proc.poll()
    assert proc.returncode is None
    cfg['pid'] = proc.pid

def kill_iokerneld(experiment):
    runcmd("sudo pkill iokerneld")
    
def gen_conf(cfg, **kwargs):
    conf = [
        "host_addr {host_addr}",
        "host_netmask {host_netmask}",
        "host_gateway {host_gateway}",
        "runtime_kthreads {runtime_kthreads}",
        "runtime_guaranteed_kthreads {runtime_guaranteed_kthreads}",
        "runtime_spinning_kthreads {runtime_spinning_kthreads}"
    ]

    if kwargs['runtime_guaranteed_kthreads'] > 0:
        conf.append("runtime_priority lc")
    else:
        conf.append("runtime_priority be")

    conf += kwargs.get('custom_conf', [])

    config_path = "{}/config".format(cfg['path'])
    with open(config_path, "w") as f:
        f.write("\n".join(conf).format(**kwargs) + "\n")

    return config_path

def launch_runtime(cfg, experiment):
    os.makedirs(cfg['path'])
    
    config_path = gen_conf(cfg, **cfg)

    binary = cfg['binary']
    args = cfg['args'].format(**cfg)

    fullcmd = "ulimit -S -c 0 && "
    do_sudo = cfg.get('sudo', False)
    for c in cfg.get('custom_conf', []):
      do_sudo |= "enable_directpath" in c
    if do_sudo:
        fullcmd += "exec sudo"
    else:
        fullcmd += "exec"
    fullcmd += " {bin} {config} {args} > {path}/runtime.out 2> {path}/runtime.err"

    fullcmd = fullcmd.format(bin=binary, config=config_path, args=args, path=cfg['path'])

    for cmd in cfg.get('before', []):
        FUNCTION_REGISTRY[cmd]()

    tm = experiment['tm']
    proc = launch(fullcmd)
    tm.append_proc(proc)

def launch_remote(usr, host, cmd, experiment):
    tm = experiment['tm']
    proc = launch('ssh -tt {}@{} \'{}\''.format(usr, host, cmd))
    tm.append_remote_proc(proc)
    time.sleep(10)

def launch_apps(experiment):
    tm = experiment['tm']
    for cfg in experiment['hosts'][CLIENT]['apps']:
        tm.new_thread(target=launch_runtime,
                      args=(cfg, experiment))

def run_client(experiment):
    launch_iokerneld(experiment)
    launch_apps(experiment)

def run_server(cfg, experiment):
    godebug = ''
    if cfg['syncpreemptoff']:
        godebug = 'GODEBUG=syncpreemptoff=1 '
    if cfg['asyncpreemptoff']:
        godebug = 'GODEBUG=asyncpreemptoff=1 '
    cmd = godebug + 'GOMAXPROCS={procs} PREEMPT_INFO={preempt_info} GOFORCEPREEMPTNS={preempt_quantum} UINTR={UINTR} SYSMON_FREQ_NETPOLL={sysmon_freqpoll} numactl --cpunodebind={numanode} --membind={numanode} {binary}  --keys_mil 10 --valsz 64 -port={port} -dir=\"{dataset}\" 2>&1 | ts %s > {outpath}'.format(**cfg)
    server = launch_remote(USERNAME, SERVER, cmd, experiment)
   
def execute_experiment(experiment, wait_time=60):
    INITLOGGING(experiment)

    experiment['tm'] = ThreadManager()
    
    run_server(experiment['hosts'][SERVER], experiment)

    run_client(experiment)

    time.sleep(wait_time)

    experiment['tm'].join_all_proc()
    kill_iokerneld(experiment)

    experiment['tm'].kill_all_remote_proc()

def run(
    go_variant='unmodified', 
    procs=8, 
    preempt_mechanism='signal', 
    preempt_quantum_us=10000, 
    asyncpreemptoff=False, 
    syncpreemptoff=False, 
    protocol='http', 
    short_percent=0.99, 
    mpps=0.3, 
    start_mpps=0, 
    samples=30, 
    runtime=120
):
    """Run experiments with different configurations.
    Args:
        go_variant (str): 'unmodified' or 'aspen'.
        procs (int): Number of processors used by the Badger server.
        preempt_mechanism (str): Preemption type, either 'uintr' or 'signal'.
        preempt_quantum_us (int): Preemption quantum in microseconds.
        asyncpreemptoff (bool): Whether asynchronous preemption (uintr or signal) is disabled. 
                                If True, only compiler-based preemption is used, so 
                                the results represent for compiler-based preemption.
        syncpreemptoff (bool): Whether synchronous preemption (compiler-based preemption) is disabled. 
                               If True, only uintr/signal preemption is used, based on `preempt_mechanism`.
        protocol (str): use 'http'.
        short_percent (float): Fraction of short requests.
        mpps (float): Maximum data points.
        start_mpps (float): Value at which data collection starts.
        samples (int): Number of data points to collect.
        runtime (int): Duration (in seconds) for each data point collection.
    """

    client_result_path = os.path.join(EXP_PATH, 'result', 'fig7')
    os.makedirs(client_result_path, exist_ok=True)

    sysmon_freqpoll = 1 if go_variant == 'aspen' else 0
    
    exp = new_experiment(go_variant, procs, preempt_mechanism, preempt_quantum_us, asyncpreemptoff, syncpreemptoff)
    exp['path'] = os.path.join(client_result_path, exp['name'])
    os.makedirs(exp['path'])

    server = add_server_app(exp, procs, preempt_mechanism, preempt_quantum_us, sysmon_freqpoll, asyncpreemptoff, syncpreemptoff, protocol)
    
    client_apps = add_client_apps(exp, server, directpath=True, protocol=protocol, short_percent=short_percent, mpps=mpps, start_mpps=start_mpps, samples=samples, runtime=runtime)
    
    finalize_client_cohort(client_apps)

    execute_experiment(exp, wait_time = (runtime+10) * samples)


# To make sure the following commands would not request for password again.
launch("sudo whoami")

if not validate_machine_info():
    exit(1)

# TEST
# run(go_variant='aspen', procs=8, preempt_mechanism='uintr', preempt_quantum_us=50, asyncpreemptoff=False, syncpreemptoff=True, protocol='http', short_percent=0.99, mpps=0.29, start_mpps=0.19, samples=10, runtime=120)

SAMPLES = 40

# Running 'unmodified Go (10 ms)'
run(go_variant='unmodified', procs=8, preempt_mechanism='signal', preempt_quantum_us=10000, asyncpreemptoff=False, syncpreemptoff=False, protocol='http', short_percent=0.99, mpps=SAMPLES/100, start_mpps=0.0, samples=SAMPLES, runtime=120)

# Running 'Aspen-Go Signals (50 μs)'
run(go_variant='aspen', procs=8, preempt_mechanism='uintr', preempt_quantum_us=50, asyncpreemptoff=False, syncpreemptoff=True, protocol='http', short_percent=0.99, mpps=SAMPLES/100, start_mpps=0.0, samples=SAMPLES, runtime=120)

# Running 'Aspen-Go UINTR (50 μs)'
run(go_variant='aspen', procs=8, preempt_mechanism='signal', preempt_quantum_us=50, asyncpreemptoff=False, syncpreemptoff=True, protocol='http', short_percent=0.99, mpps=SAMPLES/100, start_mpps=0.0, samples=SAMPLES, runtime=120)

# Running 'Aspen-Go Compiler (50 μs)'
run(go_variant='aspen', procs=8, preempt_mechanism='uintr', preempt_quantum_us=50, asyncpreemptoff=True, syncpreemptoff=False, protocol='http', short_percent=0.99, mpps=SAMPLES/100, start_mpps=0.0, samples=SAMPLES, runtime=120)
# run(go_variant='aspen', procs=8, preempt_mechanism='signal', preempt_quantum_us=50, asyncpreemptoff=True, syncpreemptoff=False, protocol='http', short_percent=0.99, mpps=SAMPLES/100, start_mpps=0.0, samples=SAMPLES, runtime=120)

# Running 'unmodified Go (50 μs)'
run(go_variant='unmodified', procs=8, preempt_mechanism='signal', preempt_quantum_us=50, asyncpreemptoff=False, syncpreemptoff=False, protocol='http', short_percent=0.99, mpps=SAMPLES/100, start_mpps=0.0, samples=SAMPLES, runtime=120)

# run(go_variant='aspen', procs=8, preempt_mechanism='uintr', preempt_quantum_us=50, asyncpreemptoff=False, syncpreemptoff=False, protocol='http', short_percent=0.99, mpps=SAMPLES/100, start_mpps=0.0, samples=SAMPLES, runtime=120)
# run(go_variant='aspen', procs=8, preempt_mechanism='signal', preempt_quantum_us=50, asyncpreemptoff=False, syncpreemptoff=False, protocol='http', short_percent=0.99, mpps=SAMPLES/100, start_mpps=0.0, samples=SAMPLES, runtime=120)
