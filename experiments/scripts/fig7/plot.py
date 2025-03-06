import os
import math
import pandas as pd
import matplotlib.pyplot as plt

import matplotlib
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42

NSHORTCLIENT = 1
NLONGCLIENT = 1
color = ['black', '#56B4E9',  '#D62728',  '#E69600', '#CC7AA8', 'darkseagreen', 'sienna' , 'purple']
linestyle = ['solid', (5, (3, 1)),  (0, (1, 0.7)),  (0, (4, 1, 1, 1)),  (5, (7.5, 1))]

def output_to_csv(filepath):
    data_lines = []
    outpath = os.path.join(filepath, 'runtime.out')
    with open(outpath, 'r') as file:
        for line in file:
            if line.startswith('Distribution,') or line.startswith('zero,'):
                data_lines.append(line.strip())  # Strip to remove newlines

        csvpath = os.path.join(filepath, 'result.csv')
    
    with open(csvpath, 'w') as csvfile:
        for line in data_lines:
            csvfile.write(line + '\n') 

def read_data(path, type, percent):
    filename = path
    if type == 'long':
        filename = os.path.join(filename, 'long/result.csv')
    elif type == 'short':
        filename = os.path.join(filename, 'short/result.csv')
    else:
        print("wrong type!")
        exit(-1)

    df = pd.read_csv(filename)
    rps = df[' Actual'].tolist()
    th = None
    if percent == 'median':
        th = df[' Median'].tolist()
    elif percent == '90th':
        th = df[' 90th'].tolist()
    elif percent == '99th':
        th = df[' 99th'].tolist()
    elif percent == '99.5th':
        th = df[' 99.5th'].tolist()
    elif percent == '99.9th':
        th = df[' 99.9th'].tolist()
    else:
        print("wrong percent type!")
        exit(-1)
    
    for i in range(len(rps)):
        rps[i] = rps[i]
        rps[i] /= 1000
        th[i] = float(th[i])
        if math.isinf(th[i]):
            th[i] = 1e6
    
    for i in range(1, len(rps)):
        if rps[i] < rps[i-1]:
            rps = rps[:i]
            th = th[:i]
            break 

    return rps, th


def plot(path, data, percent):
    fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(6, 4.3), gridspec_kw={'height_ratios': [1, 1], 'hspace': 0.55})

    keys = [('unmodified', 'signal', 10000), ('unmodified', 'signal', 50), ('aspen', 'signal-syncpreemptoff', 50), ('aspen', 'uintr-syncpreemptoff', 50), ('aspen', 'uintr-asyncpreemptoff', 50)]
    colors = ['black',  '#CC7AA8',  '#56B4E9', '#D62728',  '#E69600', '#3A86FF', '#FFBE0B']
    labels = [r'unmodified Go (10 ms)', r'unmodified Go (50 $\mu$s)', r'Aspen-Go Signals (50 $\mu$s)', r'Aspen-Go UINTR (50 $\mu$s)', r'Aspen-Go Compiler (50 $\mu$s)']

    FS = 11

    for i in range(len(keys)):
        key = keys[i]
        rps, th = data['short'][key]
        ax1.plot(rps, th, linewidth=2.5, linestyle=linestyle[i], c=colors[i], label=labels[i])

    ax1.set_ylim(bottom=0, top=1000)
    ax1.set_xlabel('Load (KRPS)', fontsize=FS+1) 
    if percent == 'median':
        ax1.set_ylabel(r'median latency ($\mu$s)', fontsize=FS)
    elif percent == '90th':
        ax1.set_ylabel(r'p90 latency ($\mu$s)', fontsize=FS)
    elif percent == '99th':
        ax1.set_ylabel(r'99% Latency ($\mu$s)', fontsize=FS)
    elif percent == '99.5th':
        ax1.set_ylabel(r'p99.5 latency ($\mu$s)', fontsize=FS)
    elif percent == '99.9th':
        ax1.set_ylabel(r'99.9% latency ($\mu$s)', fontsize=FS)
    ax1.set_xlim(left=0, right=300)
    ax1.set_xticks([0, 100, 200, 300])
    ax1.text(0.06, 0.9, "BadgerDB GET", transform=ax1.transAxes, 
         fontsize=FS+1, verticalalignment='top', horizontalalignment='left')

    for i in range(len(keys)):
        key = keys[i]
        rps, th = data['long'][key]
        ax2.plot(rps, th, linewidth=2.5, linestyle=linestyle[i], c=colors[i], label=labels[i])
    ax2.set_ylim(bottom=0, top=10000)
    ax2.set_xlabel('Load (KRPS)', fontsize=FS+1) 
    if percent == 'median':
        ax2.set_ylabel(r'median latency (ms)', fontsize=FS)
    elif percent == '90th':
        ax2.set_ylabel(r'p90 latency (ms)', fontsize=FS)
    elif percent == '99th':
        ax2.set_ylabel(r'99% Latency (ms)', fontsize=FS)
    elif percent == '99.5th':
        ax2.set_ylabel(r'p99.5 latency (ms)', fontsize=FS)
    elif percent == '99.9th':
        ax2.set_ylabel(r'99.9% Latency (ms)', fontsize=FS)
    ax2.set_xlim(left=0, right=3)
    ax2.set_xticks([0, 1, 2, 3])
    ax2.set_yticks([0, 2000, 4000, 6000, 8000, 10000], [0, 2, 4, 6, 8, 10])
    ax2.text(0.06, 0.9, "BadgerDB RangeSCAN", transform=ax2.transAxes, 
         fontsize=FS+1, verticalalignment='top', horizontalalignment='left')

    handles, labels_ = ax1.get_legend_handles_labels() 
    adj_handles = [handles[0], handles[2], handles[4],  handles[1], handles[3]]
    adj_labels = [labels_[0], labels_[2], labels_[4], labels_[1], labels_[3]]
    fig.legend(adj_handles, adj_labels, loc="upper center", ncol=2, frameon=False, fontsize=FS+1, columnspacing=1.2, handlelength=3.1,  handletextpad=0.6, bbox_to_anchor=(0.5, 1.03)) #, handletextpad=0.22)

    plt.subplots_adjust(top=0.79, bottom=0.11, left=0.13, right=0.95)
    plt.savefig('{}/{}.pdf'.format(path, percent))
    plt.show()


if __name__ == '__main__':
    SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__)) 
    SCRIPT_PATH = os.path.dirname(SCRIPT_PATH)              # Script path
    EXP_PATH = os.path.dirname(SCRIPT_PATH)                 # Experiment path
    RESULT_PATH = os.path.join(EXP_PATH, 'result', 'fig7') # Result path

    data = {'median': {'short': {}, 'long': {}}, 
            '90th':  {'short': {}, 'long': {}}, 
            '99th':  {'short': {}, 'long': {}},
            '99.5th':  {'short': {}, 'long': {}},
            '99.9th':  {'short': {}, 'long': {}}}
    
    for exp in os.listdir(RESULT_PATH):
        if 'plot' in exp or 'tmp' in exp or 'figures' in exp or 'bimodal' in exp or 'short' in exp:
            continue
        if 'unmodified' not in exp and 'syncpreemptoff' not in exp:
            continue
        exp_path = os.path.join(RESULT_PATH, exp)
        tag = exp.split('-')
        govariant = tag[1]
        mechanism = tag[3]
        quantum = int(tag[4])
        if 'asyncpreemptoff' in exp:
            mechanism += '-asyncpreemptoff'
        elif 'syncpreemptoff' in exp:
            mechanism += '-syncpreemptoff'
      
        if quantum != 50 and quantum != 10000: 
            continue
        print(exp_path, govariant, mechanism, quantum)
        output_to_csv(os.path.join(exp_path, 'short'))
        output_to_csv(os.path.join(exp_path, 'long'))
        for percent in ['median', '90th', '99th',  '99.5th', '99.9th']:
            for type in ['short', 'long']:
                data[percent][type][(govariant, mechanism, quantum)] = read_data(exp_path, type, percent)
        

    fig_path = RESULT_PATH
    for percent in ['99.9th']:
        plot(fig_path, data[percent], percent)