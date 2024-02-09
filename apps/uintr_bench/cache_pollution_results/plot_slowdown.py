import sys
import matplotlib.pyplot as plt
from matplotlib import ticker
import pandas as pd 
import statistics

bench = sys.argv[1]

T = [100, 50, 20, 15, 10, 5, 3, 2]
color = ['black', '#D62728', '#56B4E9', 'mediumseagreen', '#E69600',  '#CC7AA8', 'darkorange', 'salmon', 'skyblue', 'pink']

def get_baseline(bench, work):
    df = pd.read_csv('{}/{}/result.csv'.format(bench, work))
    return float(df['100000000:exe'].tolist()[-1])

def get_slowdown(base, bench, work):
    df = pd.read_csv('{}/{}/result.csv'.format(bench, work))
    slowdown = []
    for t in T:
        exe = float(df['{}:exe'.format(t)].tolist()[-1])
        slowdown.append((exe-base)/base)
    return slowdown

def plot_slowdown():
    plt.figure(figsize=(4, 2))

    base1 = get_baseline(bench, '{}*{}'.format(bench, 1))
    k = 0
    mx = 0
    for i in [1, 2, 4, 6, 8]:
        work = '{}*{}'.format(bench, i)
        # base = get_baseline(bench, work)
        base = base1 * i
        slowdown = get_slowdown(base, bench, work)
        plt.plot(T, slowdown, linewidth=1, marker='o', markersize=3, markeredgewidth=0.8, c=color[k], markerfacecolor='none', label='#threads = {}'.format(i))
        k += 1
        mx = max(mx, slowdown[-1])
        print(bench, work, slowdown)    

    # plt.legend(fontsize=7.5, ncol=4, loc='upper center', columnspacing=0.5, bbox_to_anchor=(0.5, 1.35), frameon=False, handlelength=1)
    # plt.legend(loc='upper right', fontsize=7)
    plt.legend(fontsize=7)

    plt.xscale("log")
    plt.xlim(max(T)*1.2, min(T)/1.2)
    if mx < 0.7:
        plt.ylim(0, 0.7)
    plt.xticks(T, T, fontsize=8)
    # plt.yticks([0, 1, 2, 3, 4, 5], fontsize=8)
    plt.gca().yaxis.set_major_formatter(ticker.PercentFormatter(1, decimals=0))
    plt.axhline(y=0.1, linewidth=1, linestyle='--', color='grey')
    plt.xlabel('Preemption quantum ($\mu$s)', fontsize=9)
    plt.ylabel('Preemption slowdown', fontsize=9)

    plt.tight_layout()
    # plt.subplots_adjust(left=0.12, right=0.97, top=0.8, bottom=0.2)
    plt.savefig('{}/slowdown.pdf'.format(bench))
    plt.show()
    

plot_slowdown()

