import matplotlib.pyplot as plt
import pandas as pd
import os
import math 
from functools import cmp_to_key

import matplotlib
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42

color = ['black', '#D62728', '#CC7AA8', '#E69600', '#56B4E9', 'darkseagreen', 'sienna' , 'purple']
linestyle = ['solid',   (0, (4, 1, 1, 1)),  (5, (7.5, 1)), (5, (3, 1)),   (0, (1, 0.7)), ]

options = ['non-preemptive', 'aspen', 'aspen_wo2queue', 'aspen_wo2queue_woskip', 'libpreemptible']
option_names = ['Non-preemptive', 'Aspen', 'Aspen (w/o 2queues)', 'Aspen (w/o 2queues) (w/o skip)', r'LibPreemptible$^{*}$']

QUANTUM = {
    'non-preemptive': 100000000,
    'aspen': 5,
    'aspen_wo2queue': 5,
    'aspen_wo2queue_woskip': 5,
    'libpreemptible': [5, 100, 10, 15, 20, 4, 6, 3, 7, 2, 8, 9, 30, 40, 50, 60, 70, 80, 90, 11, 12, 13, 14, 16, 17, 18, 19, 21, 25],
}

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__)) 
SCRIPT_PATH = os.path.dirname(SCRIPT_PATH)              # Script path
EXP_PATH = os.path.dirname(SCRIPT_PATH)                 # Experiment path
RESULT_PATH = os.path.join(EXP_PATH, 'result', 'fig10') # Result path


def find_latest_running(option, quantum):
    option_path = os.path.join(RESULT_PATH, option, str(quantum))
    subfolders = [f for f in os.listdir(option_path) if os.path.isdir(os.path.join(option_path, f))]
    
    # Filter folders that match the "run.YYYYMMDDHHMMSS" format
    subfolders = [f for f in subfolders if f.startswith("run.") and f[4:].isdigit()]
    
    print('subfolders:', subfolders)

    if not subfolders:
        return None 
    
    # Sort folders by their numeric timestamp (YYYYMMDDHHMMSS)
    latest_folder = max(subfolders, key=lambda f: f[4:])  
    
    # Return the folder with the latest running.
    return os.path.join(option_path, latest_folder)

ExpectedDataPoints = 20
def read_99_9th(option, quantum, type):
    path = find_latest_running(option, quantum)
    df = pd.read_csv('{}/{}.csv'.format(path, type))
    if type == 'total':
        rps = df[' TotalRPS'].tolist()
    else:
        rps = df[' Actual'].tolist()
    lat = df[' 99.9th'].tolist()
    for i in range(len(rps)):
        rps[i] /= 1000
        lat[i] = float(lat[i])
        if math.isinf(lat[i]):
            lat[i] = 1e6
    
    for i in range(1, len(rps)):
        if rps[i] < rps[i-1]:
            rps = rps[:i]
            lat = lat[:i]
            break

    while len(rps) < ExpectedDataPoints:
        rps.append(rps[-1] / 20 * 21)
        lat.append(1e6)
    
    return rps, lat

def comp(x, y):
    if int(x[1]) == int(y[1]):
        return -1 if x[0] > y[0] else 1
    else:
        return -1 if int(x[1]) < int(y[1]) else 1

def get_libpreemptible():
    res_all_quanta = {}
    for quantum in QUANTUM['libpreemptible']:
        get_rps, get_lat = read_99_9th('libpreemptible', quantum, 'get')
        scan_rps, scan_lat = read_99_9th('libpreemptible', quantum, 'scan')
        res_all_quanta[quantum] = {'get_rps': get_rps, 'get_lat': get_lat, 'scan_rps': scan_rps, 'scan_lat': scan_lat}

    final_get_rps, final_get_lat = [], []
    final_scan_rps, final_scan_lat = [], []
    dp_unit = 0.08
    dp_num = 20
    for i in range(0, dp_num):
        mpps = dp_unit * (i+1)
        res = []
        for quantum in QUANTUM['libpreemptible']:
            get_lat = res_all_quanta[quantum]['get_lat'][i]
            scan_lat = res_all_quanta[quantum]['scan_lat'][i]
            res.append([quantum, get_lat, scan_lat])

        sorted_res = sorted(res, key=cmp_to_key(comp))
        best_quantum = sorted_res[0][0]
        final_get_rps.append(res_all_quanta[best_quantum]['get_rps'][i])
        final_get_lat.append(res_all_quanta[best_quantum]['get_lat'][i])
        final_scan_rps.append(res_all_quanta[best_quantum]['scan_rps'][i])
        final_scan_lat.append(res_all_quanta[best_quantum]['scan_lat'][i])
        
        print('LibPreemptible: best quantum {} for mpps {}'.format(best_quantum, mpps))
    
    return final_get_rps, final_get_lat, final_scan_rps, final_scan_lat


def plot(tail='99.9th'):
    data = {'get': [], 'scan': [], 'total': [], 'label': []}
    
    for i in range(4):
        option = options[i]
        name = option_names[i]
        quantum = QUANTUM[option]
        get_rps, get_lat = read_99_9th(option, quantum, 'get')
        scan_rps, scan_lat = read_99_9th(option, quantum, 'scan')
        print('get_rps:', get_rps)
        data['get'].append({'rps': get_rps, 'lat': get_lat})
        data['scan'].append({'rps': scan_rps, 'lat': scan_lat})
        data['label'].append(name)

    get_rps, get_lat, scan_rps, scan_lat = get_libpreemptible()
    data['get'].append({'rps': get_rps, 'lat': get_lat})
    data['scan'].append({'rps': scan_rps, 'lat': scan_lat})
    data['label'].append(r'LibPreemptible$^{*}$')

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6, 2.65))

    type = 'get'
    for i in range(len(data[type])):
        ax1.plot(data[type][i]['rps'], data[type][i]['lat'], linestyle=linestyle[i], linewidth=2, c=color[i], markerfacecolor='none', label=data['label'][i])    
    ax1.set_ylim(bottom=0, top=50)
    ax1.set_xlim(left=0, right=1600)
    ax1.set_xticks([400, 800, 1200, 1600])
    ax1.set_xlabel('Load (KRPS)', fontsize=13, labelpad=7)
    ax1.set_ylabel(r'99.9% Latency ($\mu$s)', fontsize=13, labelpad=7)
    ax1.text(0.06, 0.93, "GET", transform=ax1.transAxes, 
         fontsize=13, verticalalignment='top', horizontalalignment='left')
    
    type = 'scan'
    for i in range(len(data[type])):
        ax2.plot(data[type][i]['rps'], data[type][i]['lat'], linestyle=linestyle[i], linewidth=2, c=color[i],   markerfacecolor='none', label=data['label'][i])    
    ax2.set_ylim(bottom=0, top=1000)
    ax2.set_xlim(left=0, right=80)
    ax2.set_xticks([20, 40, 60, 80])
    ax2.set_xlabel('Load (KRPS)', fontsize=13, labelpad=7)
    ax2.text(1.43, 0.93, "SCAN", transform=ax1.transAxes, 
         fontsize=13, verticalalignment='top', horizontalalignment='left')

    handles, labels = ax1.get_legend_handles_labels()
    adj_handles = [handles[0], handles[4], handles[2], handles[3], handles[1]]
    adj_labels = [labels[0], labels[4], labels[2], labels[3], labels[1]] 
    fig.legend(adj_handles, adj_labels, loc="upper center", ncol=3, frameon=False, fontsize=11, handlelength=2.4, columnspacing=0.7, handletextpad=0.5, bbox_to_anchor=(0.5, 1.04))

    plt.tight_layout()
    plt.subplots_adjust(left=0.098, right=0.97, top=0.79, bottom=0.19)
    plt.savefig(os.path.join(RESULT_PATH, 'fig10.pdf'))
    plt.show()


plot()
