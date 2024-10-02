import threading
import os
import sys
import time
import random
import psutil
import logging
import subprocess
from datetime import datetime

LOGGER = logging.getLogger('experiment')
logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.DEBUG)

NETPFX = "192.168.1"
NETMASK = "255.255.255.0"

def IP(node):
    assert node > 0 and node < 255
    return "{}.{}".format(NETPFX, node)

GATEWAY = IP(1)
CLIENT = "client"
SERVER = "server"

def alloc_ip(experiment):
    ip = IP(experiment['nextip'])
    experiment['nextip'] += 1
    return ip

FUNCTION_REGISTRY = {}

def register_fn(name, fn):
  global FUNCTION_REGISTRY
  FUNCTION_REGISTRY[name] = fn

def sleep_5(cfg, experiment):
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
    # _reset_log()
    _hostname = subprocess.check_output("hostname -s", shell=True).strip().decode('utf-8')
    fh = logging.FileHandler('{}/pylog.{}.log'.format(exp['path'], _hostname))
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    LOGGER.addHandler(fh)

class ThreadManager:

    def __init__(self):
        self.procs = {}
        self.procnames = {}
        self.proclock = threading.Lock()
        self.event = threading.Event()
        self.clientgo = threading.Event()

    def release_client(self):
        self.clientgo.set()

    def client_wait(self):
        self.clientgo.wait()

    def complete(self):
        self.event.set()
        self.clientgo.set()

    def proc_wait(self, proc):
        with self.proclock:
          self.procs[proc.pid] = proc
        # print('proc wait starts:', proc)
        proc.wait()
        # print('proc wait ends:', proc)
        self.complete()

    def append_proc(self, proc, procname):
        with self.proclock:
          self.procs[proc.pid] = proc
          self.procnames[proc.pid] = procname
    
    def join_all_proc(self):
        for p in self.procs.values():
            p.wait()
    
    def forcekill_all_proc(self):
        for pname in self.procnames.values():
            runcmd('sudo pkill {}'.format(pname))

    def is_done(self):
        return self.event.is_set()

    # def block_on_procs(self):
    #     self.event.wait()
    #     return poll_procs(*self.procs.values(), done=True)

    # def kill(self):
    #     with self.proclock:
    #       procs = list(self.procs.values())[:]
    #     for p in procs:
    #         kill_proc(p)

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

    def monitor_in_thread(self, proc):
        self.new_thread(ThreadManager.proc_wait, (self, proc))

def runcmd(*args, **kwargs):
    assert 'outp' not in kwargs
    assert len(args) == 1
    return _runcmd(args[0], True, **kwargs)

def _runcmd(cmdstr, outp, suppress=False, **kwargs):
    # print("runcmd:", cmdstr)
    kwargs['executable'] = kwargs.get("executable", "/bin/bash")
    kwargs['cwd'] = kwargs.get('cwd', "./")
    pfn = LOGGER.debug if True or suppress else LOGGER.info
    if outp:
        pfn("running {%s}: " % cmdstr)
        # res = subprocess.check_output(cmdstr, shell=True, **kwargs)
        subprocess.run(cmdstr, shell=True, **kwargs)
#        pfn("%s\n" % res.strip())
        # return res
    else:
        p = subprocess.Popen(cmdstr, shell=True,
                             stdin=subprocess.PIPE, **kwargs)
        LOGGER.info("[%04d]: launched {%s}" % (p.pid, cmdstr))
        return p

def launch(*args, **kwargs):
    assert 'outp' not in kwargs
    assert len(args) == 1
    return _runcmd(args[0], False, **kwargs)

def launch_remote(usr, host, cmd):
    return launch('ssh -t -t {}@{} \'{}\''.format(usr, host, cmd))

def new_experiment(path, **kwargs):
    x = {
        'name': "run.{}".format(datetime.now().strftime('%Y%m%d%H%M%S')),
        'hosts': {},
        'nextip': 100,
        'nextport': 5000 + random.randint(0, 255),
        'before': [],
        'after': [],
        'path': path,
    }
    if kwargs.get('name'):
        x['name'] += kwargs['name']
    return x


def add_host_to_exp(experiment, host):
    experiment['hosts'][host] = {
        'apps': [],
        'iokernel': {
            'binary': "./iokerneld",
            'scheduler': 'simple',
        },
    }

def add_app(experiment, app, host, **kwargs):
    if not host in experiment['hosts']:
        add_host_to_exp(experiment, host)
    app['host'] = host
    app['before'] = app.get('before', [])
    app['after'] = app.get('after', [])
    app['custom_conf'] = app.get('custom_conf', [])
    experiment['hosts'][host]['apps'].append(app)

def new_server_instance(experiment, threads=24, **kwargs):
    x = {
        'name': kwargs.get('name', "server"),
        # 'ip': alloc_ip(experiment),
        'ip': "192.168.1.100",
        'port': 5000,
        'threads': threads,
        'guaranteed': threads,
        'spin': threads,
        'app': kwargs.get('name', "dataframe"),
        'binary': "./apps/rocksdb_concord/rocksdb_server",
        'quantum': kwargs.get('quantum', 100000000),
        'hard_quantum': kwargs.get('hard_quantum', 100000000),
        'custom_conf': ['enable_directpath 1'],
        'args': 'udpconn 24 32'
    }
    add_app(experiment, x, host=SERVER)

def update_server_quantum(experiment, quantum, hard_quantum=100000000):
    experiment['hosts'][SERVER]['apps'][0]['quantum'] = quantum
    experiment['hosts'][SERVER]['apps'][0]['hard_quantum'] = hard_quantum


iokernel_running = False

def start_server_iokerneld(experiment):
    global iokernel_running
    if iokernel_running == True:
        return
    else:
        iokernel_running = True

    cfg = experiment['hosts'][SERVER].get('iokernel', {})
    binary = cfg.get('binary', './iokerneld')
    scheduler = cfg.get('scheduler', 'simple')
    cores_setting = cfg.get('corelimit', 'numanode 1')
    options = cfg.get('options', 'nobw noht nicpci 0000:b5:00.1')
    logpath = os.path.join(experiment['path'], 'iokernel.log')
    proc = launch("sudo {} {} {} {} 2>&1 | ts %s > {}".format(
        binary, scheduler, cores_setting, options, logpath))
    for i in range(10):
        if os.system("grep -q 'running dataplane' {}".format(logpath)) == 0:
            break
        time.sleep(1)
        proc.poll()
        if proc.returncode is not None:
            break

    proc.poll()
    print("iokernel returncode:", proc.returncode)
    assert proc.returncode is None
    cfg['pid'] = proc.pid
    # print('**** iok pid:', proc.pid)
    # experiment['tm'].append_proc(proc)

def kill_server_iokerneld(experiment):
    runcmd("sudo pkill iokerneld")
    
def gen_conf(filename, experiment, mac=None, **kwargs):
    conf = [
        "host_addr {ip}",
        "host_netmask {netmask}",
        "host_gateway {gw}",
        "runtime_kthreads {threads}",
        "runtime_guaranteed_kthreads {guaranteed}",
        "runtime_spinning_kthreads {spin}",
        "runtime_uthread_quantum_us {quantum}",
        "runtime_uthread_hard_quantum_us {hard_quantum}",
    ]
    if mac:
        conf.append("host_mac {mac}")

    # HACK
    if kwargs['guaranteed'] > 0:
        # if not kwargs.get('enable_watchdog', False):
        #     conf.append("disable_watchdog true")
        conf.append("runtime_priority lc")
    else:
        conf.append("runtime_priority be")

    conf += kwargs.get('custom_conf', [])
    
    with open(filename, "w") as f:
        f.write("\n".join(conf).format(
            netmask=NETMASK, gw=GATEWAY, mac=mac, **kwargs) + "\n")

def launch_runtime(cfg, experiment):
    assert 'args' in cfg

    binary = cfg.get('binary')

    config_path = "{}/server.config".format(experiment['path'])
    gen_conf(config_path, experiment, **cfg)

    args = cfg['args'].format(**cfg)
    envs = " ".join(cfg.get('env', []))

    fullcmd = "ulimit -S -c 0 && "
    do_sudo = cfg.get('sudo', False)
    for c in cfg.get('custom_conf', []):
      do_sudo |= "enable_directpath" in c
    if do_sudo:
        fullcmd += "exec sudo {envs}"
    else:
        fullcmd += "{envs} exec"

    fullcmd += " {bin} {config} {args} > {path}/runtime.out 2> {path}/runtime.err"

    fullcmd = fullcmd.format(envs=envs, bin=binary, config=config_path, args=args, path=experiment['path'])

    for cmd in cfg.get('before', []):
        FUNCTION_REGISTRY[cmd](cfg, experiment)

    tm = experiment['tm']

    if 'rocksdb' in binary:
        _runcmd("sudo rm -rf /tmp/my_db", True)

    proc = launch(fullcmd)
    tm.append_proc(proc, 'rocksdb')

    for cmd in cfg.get('after', []):
        FUNCTION_REGISTRY[cmd](cfg, experiment)


def launch_server_apps(experiment):
    tm = experiment['tm']
    for cfg in experiment['hosts'][SERVER]['apps']:
        launch_runtime(cfg, experiment)
        # tm.new_thread(target=launch_runtime,
        #               args=(cfg, experiment))

def go_host(experiment):
    experiment['tm'] = ThreadManager()

    start_server_iokerneld(experiment)

    launch_server_apps(experiment)

def go_remote(experiment, **kwargs):
    p = launch_remote('l1guo', 'birch', 'python3 /data/preempt/caladan-rocksdb/run_client.py policy {} {} {}'
        .format(kwargs['system'], kwargs['mpps'], kwargs['quantum']))
    return p

def execute_experiment(experiment, **kwargs):
    for cmd in experiment.get('before', []):
        FUNCTION_REGISTRY[cmd](experiment)

    INITLOGGING(experiment)

    go_host(experiment)

    remote = go_remote(experiment, **kwargs)

    time.sleep(133*5)
    
    while True:
        remote.poll()
        print("remote ret:", remote.returncode)
        if remote.returncode is None:
            time.sleep(1)
            continue
        elif remote.returncode != 0:
            print("remote ret {} is not zero", remote.returncode)
        break

    experiment['tm'].forcekill_all_proc()
    # kill_server_iokerneld(experiment)

def run_policy(path, app, system, mpps, quantum=100000000, hard_quantum=100000000):
    if not os.path.exists(path):
        os.makedirs(path)

    # path = os.path.join(path, str(mpps))
    # if not os.path.exists(path):
    #     os.makedirs(path)

    path = os.path.join(path, system)
    if not os.path.exists(path):
        os.makedirs(path)

    path = os.path.join(path, str(quantum))
    if not os.path.exists(path):
        os.makedirs(path)
    
    # print("** new_experiment")
    exp = new_experiment(path)

    # print("** new_server_instance")
    new_server_instance(exp, app=app, quantum=quantum, hard_quantum=hard_quantum)

    # print("** execute_experiment")
    execute_experiment(exp, system=system, mpps=mpps, quantum=quantum, hard_quantum=hard_quantum)


def evaluate_policy(path, app):
    # for 50%:
    # for quantum in [50, 45, 40, 35, 30, 25, 20, 15, 12, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]:
    #     run_policy(path, app, 'libpreemptible', 0.25, quantum)
    # run_policy(path, app, 'aspen', 0.25, 4)
    # run_policy(path, app, 'aspen-noprq-periodic', 0.25, 4)
    # run_policy(path, app, 'aspen-noprq', 0.25, 4)
    # run_policy(path, app, 'base', 0.25)

    # for 5%
    # for quantum in [50, 5, 100, 90, 80, 70, 60, 45, 40, 35, 30, 25, 20, 15, 12, 10, 9, 8, 7, 6, 4, 3, 2, 1]:
    #     run_policy(path, app, 'libpreemptible', 2.0, quantum)
    # for quantum in [5]:
    #     run_policy(path, app, 'aspen-noprq-periodic', 2, quantum)
    # run_policy(path, app, 'base', 2)

    # for quantum in [50, 5, 100, 90, 80, 70, 60, 45, 40, 35, 30, 25, 20, 15, 12, 10, 9, 8, 7, 6, 4, 3, 2, 1]:
    #     run_policy(path, app, 'libpreemptible', 10, quantum)
    # run_policy(path, app, 'aspen', 10, 8)
    run_policy(path, app, 'aspen-noprq-periodic', 10, 8)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("bad argv")
        exit()
    option = sys.argv[1]
    
    if option == 'policy':
        # run_policy('rocksdb_server_log/50', app='rocksdb', system='aspen', mpps=1.5, quantum=5, hard_quantum=200)
        evaluate_policy('rocksdb_server_log/5', app='rocksdb')
        runcmd("sudo pkill iokerneld")
        