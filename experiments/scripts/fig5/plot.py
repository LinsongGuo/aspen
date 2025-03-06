import matplotlib.pyplot as plt
import pandas as pd
import os
import math 

import matplotlib
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42

color = ['black',  '#D62728',  '#E69600',  '#E69600',  '#56B4E9', '#CC7AA8', 'darkseagreen', 'sienna' , 'purple']
linestyle = ['solid',  (0, (4, 1, 1, 1)),  (5, (3, 1)), (5, (7.5, 1)),  (0, (1, 0.7)), ]

options = ['non-preemptive/100000000',  'uintr/5',  'concord/5', 'concord-fine_tuned/5', 'signal/15']
option_names = ['Non-preemptive', r'User Interrupts (5 $\mu$s)', r'CONCORD (5 $\mu$s)',   r'CONCORD fine-tuned (5 $\mu$s)', r'Signals (15 $\mu$s)'] 

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__)) 
SCRIPT_PATH = os.path.dirname(SCRIPT_PATH)              # Script path
EXP_PATH = os.path.dirname(SCRIPT_PATH)                 # Experiment path
RESULT_PATH = os.path.join(EXP_PATH, 'result', 'fig5')  # Result path


def find_latest_running(option):
    option_path = os.path.join(RESULT_PATH, option)
    subfolders = [f for f in os.listdir(option_path) if os.path.isdir(os.path.join(option_path, f))]
    
    # Filter folders that match the "run.YYYYMMDDHHMMSS" format
    subfolders = [f for f in subfolders if f.startswith("run.") and f[4:].isdigit()]
    
    if not subfolders:
        return None 
    
    # Sort folders by their numeric timestamp (YYYYMMDDHHMMSS)
    latest_folder = max(subfolders, key=lambda f: f[4:])  
    
    # Return the folder with the latest running.
    return os.path.join(option_path, latest_folder)

ExpectedDataPoints = 50
def read_99_9th(option, type):
    path = find_latest_running(option)
    df = pd.read_csv('{}/{}.csv'.format(path, type))
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
        rps.append(rps[-1] / 50 * 51)
        lat.append(1e6)
    
    return rps, lat


def plot():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6, 3))

    for i in range(len(options)):
        option = options[i]
        name = option_names[i]
        rps, lat = read_99_9th(option, 'get')
        ax1.plot(rps, lat, linestyle=linestyle[i], linewidth=2, c=color[i],  label=name)
    ax1.set_xlabel('Load (KRPS)', fontsize=13, labelpad=6) 
    ax1.set_ylabel(r'99.9% Latency ($\mu$s)', fontsize=13, labelpad=7) 
    ax1.set_ylim(bottom=0, top=50)
    ax1.set_xlim(left=0, right=1600)
    ax1.set_xticks([400, 800, 1200, 1600])
    ax1.text(0.06, 0.93, "GET", transform=ax1.transAxes, 
         fontsize=13, verticalalignment='top', horizontalalignment='left')
    
    for i in range(len(options)):
        option = options[i]
        name = option_names[i]
        rps, lat = read_99_9th(option, 'scan')
        ax2.plot(rps, lat, linestyle=linestyle[i], linewidth=2, c=color[i],  label=name)
    ax2.set_xlabel('Load (KRPS)', fontsize=13, labelpad=6) 
    ax2.set_ylim(bottom=0, top=2000)    
    ax2.set_xlim(left=0, right=84)
    ax2.set_xticks([20, 40, 60, 80])
    ax2.text(1.41, 0.93, "SCAN", transform=ax1.transAxes, 
         fontsize=13, verticalalignment='top', horizontalalignment='left')

    handles, labels = ax1.get_legend_handles_labels() 
    adjusted_handles = [handles[0], handles[2], handles[1], handles[4], handles[3]]
    adjusted_labels = [labels[0], labels[2], labels[1], labels[4], labels[3]]
    fig.legend(adjusted_handles, adjusted_labels, loc="upper center",  handlelength=2.4, columnspacing=1.5, ncol=2, frameon=False, fontsize=12, bbox_to_anchor=(0.52, 1.04))
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.7, bottom=0.18)
    plt.subplots_adjust(left=0.10, right=0.98, top=0.71, bottom=0.16)
    plt.savefig(os.path.join(RESULT_PATH, 'fig5.pdf'))
    plt.show()


plot()
