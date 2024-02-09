import sys
import matplotlib.pyplot as plt
from matplotlib import ticker
import pandas as pd 
import statistics

bench = sys.argv[1]
times = int(sys.argv[2])

T = [100, 50, 20, 10, 5, 3]
color = ['black', '#D62728', '#56B4E9',  '#E69600', 'mediumseagreen', '#CC7AA8', 'darkorange', 'salmon', 'skyblue', 'pink']

def get_baseline(bench, work):
    df = pd.read_csv('{}/{}/result.csv'.format(bench, work))
    return float(df['100000000:exe'].tolist()[-1])

def get_overhead(base, bench, work):
    df = pd.read_csv('{}/{}/result.csv'.format(bench, work))
    overhead = []
    for t in T:
        exe = float(df['{}:exe'.format(t)].tolist()[-1])
        p = int(df['{}:preempt'.format(t)].tolist()[-1])
        overhead.append((exe-base)/p*(10**6))
    return overhead


def plot_overhead():
    plt.figure(figsize=(4, 2))

    for i in range(1, times+1):
        work = '{}*{}'.format(bench, i)
        base = get_baseline(bench, work)
        overhead = get_overhead(base, bench, work)
        plt.plot(T, overhead, linewidth=1, marker='o', markersize=3, markeredgewidth=0.8, c=color[i], markerfacecolor='none', label='#threads = {}'.format(i))
        print(bench, work, overhead)    
    
    # plt.legend(fontsize=7.5, ncol=4, loc='upper center', columnspacing=0.5, bbox_to_anchor=(0.5, 1.35), frameon=False, handlelength=1)
    plt.legend(loc='upper right', fontsize=7)

    plt.xscale("log")
    plt.xlim(max(T)*1.2, min(T)/1.2)
    plt.ylim(0, 5)
    plt.xticks(T, T, fontsize=8)
    plt.yticks([0, 1, 2, 3, 4, 5], fontsize=8)
    plt.axhline(y=1, linewidth=1, linestyle='--', color='grey')
    # plt.axhline(y=2, linewidth=1, linestyle='--', color='grey')
    plt.xlabel('Preemption quantum ($\mu$s)', fontsize=9)
    plt.ylabel('Preemption overhead ($\mu$s)', fontsize=9)

    plt.tight_layout()
    # plt.subplots_adjust(left=0.12, right=0.97, top=0.8, bottom=0.2)
    plt.savefig('{}/overhead.pdf'.format(bench))
    plt.show()
    

plot_overhead()

