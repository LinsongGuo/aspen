
import threading
import re
import os
import sys
import time
import psutil
import logging
import subprocess
from datetime import datetime


###################################################################################
###                            CONFIGURATION SETTINGS                           ###
###                      Change the following before you run                    ###
###################################################################################

# You need two machines to run this experiment.
CLIENT = ''     # IP address or hostname of the client machine
SERVER = ''     # IP address or hostname of the server machine
USERNAME = ''   # Your username for both machines
PASSWD = ''     # Your password for both machines
# WARNING: Do NOT commit your password to GitHub or any public repository!

# Number of kernel threads (CPU logical cores) in the client runtime (load generator)
CLIENT_KTHREADS = 45 
# Enable hyperthreading for the client (True = enabled, False = disabled)
CLIENT_HYPERTHREAD = True
# Number of kernel threads (CPU logical cores) in the server runtime (the evaluated application: RocksDB)
CLIENT_NUMANODE = 1
# NUMA node assigned to the client runtime
SERVER_KTHREADS = 24  
# Enable hyperthreading for the server (True = enabled, False = disabled)
SERVER_HYPERTHREAD = False
# NUMA node assigned to the server runtime
SERVER_NUMANODE = 1
# Performance Recommendations:
# - Ideally, CLIENT_KTHREADS should be close to SERVER_KTHREADS * 2.
# - Hyperthreading is generally **not recommended** for the server to ensure good performance.
# - However, enabling hyperthreading on the client can provide more available cores.
# - For non-preemptive experiments, we use SERVER_KTHREADS + 1 cores in the server runtime.

# Enable DirectPath or not.
# DirectPath allows runtime cores to send and receive packets directly from the NIC,
# achieving better performance compared to when the IOKernel handles all packets.
DIRECTPATH = True

# If DirectPath is enabled, you must provide the PCI address of the NIC.
NIC_PCI = '0000:b5:00.1'  
# You can typically find the NIC PCI address using: 
#   lspci | grep -i 'ethernet'
# Regardless of whether DirectPath is enabled, you need to modify the hardcoded NIC port
# in the source file: iokernel/dpdk.c:283 (`dp.port = 1;`).
# The port is typically either 0 or 1.

# The core ID of the timer core used to send preemption in the server runtime
TIMER_CORE = 55  
# TODO: Currently, the timer core is not managed by iokernel and ksched.
# Thus a timer core ID must be manually assigned. 
# Ensure this core is not used by application threads at runtime.

#################################################################################
###                           END OF CONFIGURATION                            ###
#################################################################################


# Preemption quantq (in microseconds)
PREEMPT_QUANTUM = {
    'non-preemptive': [100000000],
    'aspen': [5],
    'aspen_wo2queue': [5],
    'aspen_wo2queue_woskip': [5],
    'libpreemptible': [5, 100, 10, 15, 20, 4, 6, 3, 7, 2, 8, 9, 30, 40, 50, 60, 70, 80, 90, 11, 12, 13, 14, 16, 17, 18, 19, 21, 25],
    # If you want shorter time to run libpreemptible, you can run ciritcal quanta [5, 100, 2, 3, 5, 8, 12, 17]
}

# Hard quantum threshold (in microseconds) 
# Threads running longer than this must be preempted and 
# will not be skipped by the preemption policy.
PREEMPT_HARD_QUANTUM  = {
    'non-preemptive': 100000000,
    'aspen': 500,
    'aspen_wo2queue': 500,
    'aspen_wo2queue_woskip': 500,
    'libpreemptible': 500
}

CLIENT_COMMAND = 'apps/loadgen/target/release/synthetic'
SERVER_COMMAND = {
    'non-preemptive': 'apps/rocksdb_concord/rocksdb_server',
    'aspen': 'apps/rocksdb_concord/rocksdb_server',
    'aspen_wo2queue': 'apps/rocksdb_concord/rocksdb_server',
    'aspen_wo2queue_woskip': 'apps/rocksdb_concord/rocksdb_server',
    'libpreemptible': 'apps/rocksdb_concord/rocksdb_server'
}

# Number of concurrent requests (user threads) per kernel thread
REQUESTS_PER_KTHREADS = 64  

# Addresses used for client and server runtime.
# No need to modify the following addresses, as they are managed by 
# Caladan's network stack instead of the Linux network stack.
RUNTIME_CLIENT_ADDR = '192.168.1.100'  # Client runtime IP address
RUNTIME_SERVER_ADDR = '192.168.1.101'  # Server runtime IP address
RUNTIME_NETMASK = '255.255.255.0'      # Subnet mask for the runtime network
RUNTIME_GATEWAY = '192.168.1.1'        # Default gateway for the runtime network

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__)) 
SCRIPT_PATH = os.path.dirname(SCRIPT_PATH) # Script path
EXP_PATH = os.path.dirname(SCRIPT_PATH)    # Experiment path
HOME_PATH = os.path.dirname(EXP_PATH)      # Project home path 

LOGGER = logging.getLogger('experiment')
logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.DEBUG)

def _reset_log():
    import sys
    for handler in LOGGER.handlers[:]: LOGGER.removeHandler(handler)
    sh = logging.StreamHandler(sys.stdout)
    LOGGER.addHandler(sh)

def INITLOGGING(exp):
    _reset_log()
    fh = logging.FileHandler('{}/commands.log'.format(exp['client_path']))
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    LOGGER.addHandler(fh)


def validate_machine_info():
    """ Validates that the required machine info is valid and verifies SSH and sudo access. """

    variables = {
        'CLIENT': CLIENT,
        'SERVER': SERVER,
        'USERNAME': USERNAME,
        'PASSWD': PASSWD
    }
    # Validate that all variables are non-empty strings
    for name, value in variables.items():
        if not isinstance(value, str) or not value.strip():
            print(f"Error: {name} is empty or not a valid string.")
            return False

    # Command to verify hostnames, username, and sudo privileges
    command = "whoami"
    try:
        output = run_server_cmd(command, use_sudo=True)
    except subprocess.CalledProcessError as e:
        print(f"SSH process failed: {e}")
        return False
    
    if isinstance(output, bytes):
        output = output.decode().strip()

    # Check if the output contains "root" to ensure the ssh and sudo work
    if output:
        match = re.search(r'root', output)
        if match:
            print("SSH and sudo verification successful.")
            return True
    
    print("SSH and sudo verification failed.")
    return False


class ThreadManager:
    def __init__(self):
        self.procs = {}
        self.server_procs = {}
        self.proclock = threading.Lock()

    def append_proc(self, proc):
        with self.proclock:
          self.procs[proc.pid] = proc

    def append_server_proc(self, proc):
        with self.proclock:
          self.server_procs[proc.pid] = proc

    def join_all_proc(self):
        procs = list(self.procs.values())
        LOGGER.info("waiting for the client runtime (load generator) to complete...")
        for p in procs:
            p.wait()
        LOGGER.info("the client runtime (load generator) has ended.")

    def kill_all_proc(self):
        """Kills a  process and all its children."""
        LOGGER.info("killing the client runtime (load generator).")
        for p in self.procs.values():
            try:
                parent = psutil.Process(p.pid)
                children = parent.children(recursive=True)

                _, alive = psutil.wait_procs(children, timeout=3)
                for child in alive:
                    child.kill()

                parent.kill()

            except psutil.NoSuchProcess:
                pass
        LOGGER.info("the client runtime (load generator) killed.")
            
    # def kill_all_server_proc(self):
    #     print('kill_all_server_proc:', self.server_procs.values())
    #     for p in self.server_procs.values():
    #         p.kill()
    #         LOGGER.info("[%04d]: the ssh process is killed." % (p.pid))

    def kill_all_server_proc(self):
        """Kills a  process and all its children."""
        LOGGER.info("killing all server processes.")
        for p in self.server_procs.values():
            try:
                parent = psutil.Process(p.pid)
                children = parent.children(recursive=True)

                _, alive = psutil.wait_procs(children, timeout=3)
                for child in alive:
                    child.kill()

                parent.kill()

            except psutil.NoSuchProcess:
                pass
        LOGGER.info("all server processes killed.")

# run_cmd is synchronous
def run_cmd(cmdstr):
    LOGGER.info("running {%s}" % cmdstr)
    res = subprocess.check_output(cmdstr, shell=True)
    return res

def run_server_cmd(cmdstr, use_sudo=False):
    if use_sudo:
        cmdstr = "echo {} | sudo -S {}".format(PASSWD, cmdstr)
    return run_cmd('ssh -tt {}@{} \'{}\''.format(USERNAME, SERVER, cmdstr))

def run_client_cmd(cmdstr, use_sudo=False):
    if use_sudo:
        cmdstr = "echo {} | sudo -S {}".format(PASSWD, cmdstr)
    return run_cmd(cmdstr)


# launch_cmd is asynchronous
def launch_cmd(cmdstr):
    p = subprocess.Popen(cmdstr, shell=True, stdin=subprocess.PIPE)
    LOGGER.info("[%04d]: launched {%s}" % (p.pid, cmdstr))
    return p

def launch_server_cmd(exp, cmdstr, logpath, use_sudo=False):
    if use_sudo:
        cmdstr = "echo {} | sudo -S {}".format(PASSWD, cmdstr)
    proc = launch_cmd(f"ssh -tt {USERNAME}@{SERVER} '{cmdstr}' >{logpath} 2>&1")
    tm = exp['tm']
    tm.append_server_proc(proc)
    return proc

def launch_client_cmd(exp, cmdstr, save_to_tm=False, use_sudo=False):
    if use_sudo:
        cmdstr = "echo {} | sudo -S {}".format(PASSWD, cmdstr)
    proc = launch_cmd(cmdstr)
    if save_to_tm:
        tm = exp['tm']
        tm.append_proc(proc)
    return proc 

def copy_file_to_server(clientpath, serverpath):
    return run_cmd('scp {} {}@{}:{}'.format(clientpath, USERNAME, SERVER, serverpath))

def server_path_exists(serverpath):
    cmd = f'ssh {USERNAME}@{SERVER} "[ -e {serverpath} ] && echo EXISTS || echo NOTFOUND"'
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.strip() == "EXISTS"

def new_experiment(option, client_path, server_path, mpps, start_mpps, samples):
    x = {
        'option': option,
        'client_path': client_path,
        'server_path': server_path,
        'mpps': mpps,
        'start_mpps': start_mpps,
        'samples': samples
    }
    x['tm'] = ThreadManager()
    return x

def generate_client_config(exp):
    conf = [
        f"host_addr {RUNTIME_CLIENT_ADDR}",
        f"host_netmask {RUNTIME_NETMASK}",
        f"host_gateway {RUNTIME_GATEWAY}",
        f"runtime_kthreads {CLIENT_KTHREADS}",
        f"runtime_guaranteed_kthreads {CLIENT_KTHREADS}",
        f"runtime_spinning_kthreads {CLIENT_KTHREADS}",
        f"runtime_priority lc",
    ]
    if DIRECTPATH:
        conf.append("enable_directpath 1")

    filepath = os.path.join(exp['client_path'], 'client.config')
    with open(filepath, "w") as f:
        f.write("\n".join(conf) + "\n")

def generate_server_config(exp, quantum):
    hard_quantum = PREEMPT_HARD_QUANTUM[exp['option']]
    if quantum > hard_quantum:
        hard_quantum = quantum

    kthreads = SERVER_KTHREADS
    if exp['option'] == 'non-preemptive':
        kthreads += 1
    conf = [
        f"host_addr {RUNTIME_SERVER_ADDR}",
        f"host_netmask {RUNTIME_NETMASK}",
        f"host_gateway {RUNTIME_GATEWAY}",
        f"runtime_kthreads {kthreads}",
        f"runtime_guaranteed_kthreads {kthreads}",
        f"runtime_spinning_kthreads {kthreads}",
        f"runtime_uthread_quantum_us {quantum}",
        f"runtime_uthread_hard_quantum_us {hard_quantum}",
        f"runtime_timer_core {TIMER_CORE}",
        f"runtime_priority lc",
    ]
    if DIRECTPATH:
        conf.append("enable_directpath 1")

    clientpath = os.path.join(exp['client_path'], 'server.config')
    with open(clientpath, "w") as f:
        f.write("\n".join(conf) + "\n")
    serverpath = os.path.join(exp['server_path'], 'server.config')
    
    copy_file_to_server(clientpath, serverpath)


def run_server(exp):
    """ Launch all server processes. """
    iokernel_path = os.path.join(HOME_PATH, 'iokerneld')
    iokernel_log = os.path.join(exp['client_path'], 'server_iokernel.log')
    noht = '' if SERVER_HYPERTHREAD else 'noht'
    nicpci = f'nicpci {NIC_PCI}' if DIRECTPATH else ''
    iokernel_cmd = f'{iokernel_path} simple numanode {SERVER_NUMANODE} {noht} nobw {nicpci}'

    clean_cmd = 'rm -rf /tmp/my_db/'

    kthreads = SERVER_KTHREADS
    if exp['option'] == 'non-preemptive':
        kthreads += 1
    runtime_path = os.path.join(HOME_PATH, SERVER_COMMAND[exp['option']])
    runtime_config = os.path.join(exp['server_path'], 'server.config')
    runtime_log = os.path.join(exp['client_path'], 'server.log')
    runtime_cmd = f'{runtime_path} {runtime_config} udpconn {kthreads} {REQUESTS_PER_KTHREADS}'

    # Launch the iokernel process in server.
    iok = launch_server_cmd(exp, iokernel_cmd, iokernel_log, use_sudo=True)
    time.sleep(10)
    status = iok.poll()
    if status is not None:
        raise Exception(f"the '{iokernel_cmd}' process in server didn't start succesfully")

    # Clean the tmp storage for rocksdb.
    run_server_cmd(clean_cmd, use_sudo=True)
    time.sleep(1)

    # Launch the server runtime (the rocksdb server).
    rocksdb_server = launch_server_cmd(exp, runtime_cmd, runtime_log, use_sudo=DIRECTPATH)
    time.sleep(10)
    status = rocksdb_server.poll()
    if status is not None:
        raise Exception(f"the '{runtime_cmd}' process in server didn't start succesfully")


def run_client(exp):
    """ Launch all client processes. """
    iokernel_path = os.path.join(HOME_PATH, 'iokerneld')
    iokernel_log = os.path.join(exp['client_path'], 'client_iokernel.log')
    noht = '' if CLIENT_HYPERTHREAD else 'noht'
    nicpci = f'nicpci {NIC_PCI}' if DIRECTPATH else ''
    iokernel_cmd = f'{iokernel_path} simple numanode {CLIENT_NUMANODE} {noht} nobw {nicpci} > {iokernel_log} 2>&1'

    runtime_path = os.path.join(HOME_PATH, CLIENT_COMMAND)
    runtime_config = os.path.join(exp['client_path'], 'client.config')
    runtime_log = os.path.join(exp['client_path'], 'client.log')
    runtime_result = exp['client_path']
    server_addr = f'{RUNTIME_SERVER_ADDR} 5000'
    runtime_cmd = (
        f"{runtime_path} --config {runtime_config} {server_addr} "
        f"--mode runtime-client --protocol rocksdb --transport udp "
        f"--threads {SERVER_KTHREADS} --mpps={exp['mpps']} --start_mpps {exp['start_mpps']} "
        f"--samples={exp['samples']} --resultpath {runtime_result} "
        f"> {runtime_log} 2>&1"
    )
    
    # Start the iokernel process in client.
    iok = launch_client_cmd(exp, iokernel_cmd, save_to_tm=False, use_sudo=True)
    # Wait until the iokernel is ready.
    for i in range(30):
        time.sleep(1)
        if os.system("grep -q 'running dataplane' {}".format(iokernel_log)) == 0:
            break
        status = iok.poll()
        if status is not None:
            raise Exception(f"the '{iokernel_cmd}' process in client didn't start succesfully")
    LOGGER.info("[%04d]: the iokernel is ready." % (iok.pid))

    # Start the client runtime (load generator).
    loadgen = launch_client_cmd(exp, runtime_cmd, save_to_tm=True, use_sudo=DIRECTPATH)
    status = loadgen.poll()
    if status is not None:
        raise Exception(f"the '{runtime_cmd}' process in client didn't start succesfully")


def evaluate(option, client_path, server_path, quantum=5, mpps=2, start_mpps=0, samples=50):
    """
    Runs an experiment with the given parameters.
    Parameters:
    - option:  'non-preemptive', 'signal', 'uintr', 'concord-fine_tuned', or 'concord'.
    - client_path: Path to the client results and logs.
    - server_path: Path to the server results and logs.
    - mpps: Total million requests per second.
    - start_mpps: Initial request rate to start the experiment.
    - samples: Number of data points taken in the interval (start_mpps, mpps].
    """
    
    exp = new_experiment(option, client_path, server_path, mpps, start_mpps, samples)

    INITLOGGING(exp)

    generate_client_config(exp)
    generate_server_config(exp, quantum)

    try:
        run_server(exp)
    except Exception as e:
        exp['tm'].kill_all_server_proc()
        LOGGER.warning(f"failed to start server processes: {str(e)}")
        return
    
    try:
        run_client(exp)
    except Exception as e:
        run_client_cmd("pkill iokerneld", use_sudo=True)
        run_client_cmd("pkill synthetic", use_sudo=True)
        exp['tm'].kill_all_proc()
        exp['tm'].kill_all_server_proc()
        LOGGER.warning(f"failed to start client processes: {str(e)}")
        return

    # Estimate the time required for all data points to complete
    wait_time = (samples + 1) * 22
    time.sleep(wait_time)

    try:
        exp['tm'].join_all_proc()
    except Exception as e:
        exp['tm'].kill_all_proc()
        LOGGER.warning(f"failed to join the client runtime (load generator).")
        pass

    try:
        run_client_cmd("pkill iokerneld", use_sudo=True)
    except Exception as e:
        LOGGER.warning(f"failed to kill the iokernel process.")
        pass
    
    try:
        exp['tm'].kill_all_server_proc()
    except Exception as e:
        LOGGER.warning(f"failed to kill the ssh processes to server.")
        pass

if __name__ == '__main__':
    if not validate_machine_info():
        exit(1)

    if len(sys.argv) < 2:
        print(f"Error: Missing argument. Choose from {list(PREEMPT_QUANTUM.keys())}.")
        exit(1)
    option = sys.argv[1]

    if option not in PREEMPT_QUANTUM:
        print(f"Error: Invalid option '{option}'. Choose from {list(PREEMPT_QUANTUM.keys())}.")
        exit(1)
    
    for quantum in PREEMPT_QUANTUM[option]:
        name = "run.{}".format(datetime.now().strftime('%Y%m%d%H%M%S'))
        client_result_path = os.path.join(EXP_PATH, 'result', 'fig10', option, str(quantum), name)
        os.makedirs(client_result_path, exist_ok=True)

        server_config_path = os.path.join(EXP_PATH, 'server_config')
        if not server_path_exists(server_config_path):
            print(f"Path {server_config_path} does not exist on {SERVER}. Please try to create.")
            exit(1)

        evaluate(option, client_result_path, server_config_path, quantum, mpps=2, start_mpps=0, samples=25)