import matplotlib.pyplot as plt
import pandas as pd 
import os
import math 

import matplotlib
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42

color = ['black',  '#D62728',  '#E69600', '#E69600', '#56B4E9',  'sienna' ]
linestyle = ['solid',   (0, (4, 1, 1, 1)), (5, (3, 1)), (5, (7.5, 1)), (0, (1, 0.7))]

options = ['non-preemptive/100000000',  'uintr/20',  'concord/20', 'concord-fine_tuned/20', 'signal/25']
option_names = ['Non-preemptive', r'User Interrupts (20 $\mu$s)', r'CONCORD (20 $\mu$s)',  r'CONCORD fine-tuned  (20 $\mu$s)', r'Signals (25 $\mu$s)'] 

name_map = {'req1': 'decay', 'req2': 'ad (Accumulation/Distribution)', 'req3': 'rmv (Rolling Mid Value)', 'req4': 'ppo (Percentage Price Oscillator)', 'req5': 'kmeans' }

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__)) 
SCRIPT_PATH = os.path.dirname(SCRIPT_PATH)              # Script path
EXP_PATH = os.path.dirname(SCRIPT_PATH)                 # Experiment path
RESULT_PATH = os.path.join(EXP_PATH, 'result', 'fig6')  # Result path


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

ExpectedDataPoints = 35
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

    while len(rps) < ExpectedDataPoints+1:
        rps.append(rps[-1] / 35 * 36)
        lat.append(1e6)
    
    return rps, lat

def plot():
    fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(1, 5, figsize=(15, 2.5))
    FS = 15
    TFS = 11
    LS = 2
    for i in range(len(options)):
        option = options[i]
        name = option_names[i]
        rps, lat = read_99_9th(option, 'req1')
        ax1.plot(rps, lat, linestyle=linestyle[i], linewidth=LS, c=color[i], label=name)
    ax1.set_xlabel('Load (KRPS)', fontsize=FS)
    ax1.set_ylim(bottom=0, top=100)
    ax1.set_ylabel(r'99.9% Latency ($\mu$s)', fontsize=FS)  
    ax1.tick_params(axis='x', labelsize=TFS)
    ax1.tick_params(axis='y', labelsize=TFS)
    ax1.text(0.06, 0.93, "decay", transform=ax1.transAxes, 
         fontsize=FS, verticalalignment='top', horizontalalignment='left')
    
    for i in range(len(options)):
        option = options[i]
        name = option_names[i]
        rps, lat = read_99_9th(option, 'req2')
        ax2.plot(rps, lat, linestyle=linestyle[i], linewidth=LS, c=color[i], label=name)
    ax2.set_xlabel('Load (KRPS)', fontsize=FS)
    ax2.set_ylim(bottom=0, top=100) 
    ax2.tick_params(axis='x', labelsize=TFS)
    ax2.tick_params(axis='y', labelsize=TFS)
    ax2.text(1.34, 0.93, "ad", transform=ax1.transAxes, 
         fontsize=FS, verticalalignment='top', horizontalalignment='left')
    
    for i in range(len(options)):
        option = options[i]
        name = option_names[i]
        rps, lat = read_99_9th(option, 'req3')
        ax3.plot(rps, lat, linestyle=linestyle[i], linewidth=LS, c=color[i], label=name)
    ax3.set_xlabel('Load (KRPS)', fontsize=FS)
    ax3.set_ylim(bottom=0, top=500)
    ax3.tick_params(axis='x', labelsize=TFS)
    ax3.tick_params(axis='y', labelsize=TFS)
    ax3.text(2.62, 0.93, "rmv", transform=ax1.transAxes, 
         fontsize=FS, verticalalignment='top', horizontalalignment='left') 

    for i in range(len(options)):
        option = options[i]
        name = option_names[i]
        rps, lat = read_99_9th(option, 'req4')
        ax4.plot(rps, lat, linestyle=linestyle[i], linewidth=LS, c=color[i], label=name)
    ax4.set_xlabel('Load (KRPS)', fontsize=FS)
    ax4.set_ylim(bottom=0, top=1000)
    ax4.tick_params(axis='x', labelsize=TFS)
    ax4.tick_params(axis='y', labelsize=TFS) 
    ax4.text(3.87, 0.93, "ppo", transform=ax1.transAxes, 
         fontsize=FS, verticalalignment='top', horizontalalignment='left')        

    for i in range(len(options)):
        option = options[i]
        name = option_names[i]
        rps, lat = read_99_9th(option, 'req5')
        ax5.plot(rps, lat, linestyle=linestyle[i], linewidth=LS, c=color[i], label=name)
    ax5.set_xlabel('Load (KRPS)', fontsize=FS)
    ax5.set_ylim(bottom=0, top=2000)
    ax5.tick_params(axis='x', labelsize=TFS)
    ax5.tick_params(axis='y', labelsize=TFS) 
    ax5.text(5.13, 0.93, "kmeans", transform=ax1.transAxes, 
         fontsize=FS, verticalalignment='top', horizontalalignment='left')        

    ax1.set_xlim(left=0, right=62)
    ax2.set_xlim(left=0, right=62)
    ax3.set_xlim(left=0, right=64)
    ax4.set_xlim(left=0, right=67)
    ax5.set_xlim(left=0, right=70)
    
    handles, labels = ax1.get_legend_handles_labels() 
    adjusted_handles = [handles[0], handles[4], handles[1], handles[2], handles[3]]
    adjusted_labels = [labels[0], labels[4], labels[1], labels[2], labels[3]]
    fig.legend(adjusted_handles, adjusted_labels, loc="upper center", ncol=5, frameon=False, fontsize=FS, handlelength=2, columnspacing=1, handletextpad=0.4, bbox_to_anchor=(0.516, 1.05)) #, handletextpad=0.22)

    # Show the plot
    plt.tight_layout()
    plt.subplots_adjust(top=0.84, bottom=0.22)
    plt.savefig(os.path.join(RESULT_PATH, 'fig6.pdf'))
    plt.show()
    
plot()