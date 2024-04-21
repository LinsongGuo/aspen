import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import ScalarFormatter
import sys 
from statistics import median

# baseline = 2.469403904 #mcf
baseline = 1.368368128 #linpack
# baseline = 1.300093952 #matmul
color = ['#D62728', '#1F77B4',  '#38A538','#FF7F0E'] # red, blue, green, orange
  
def get_median(lat):
    lat_sort = sorted(lat)
    return lat_sort[(len(lat)-1)>>1]

Num = 16
def get_exe(filename):
    df = pd.read_csv(filename)
    exes = []
    for n in range(1, Num + 1):
        exe = df['{}-exe'.format(n)].tolist()
        exes.append(exe)
    return exes 

def get_uintr(filename):
    df = pd.read_csv(filename)
    uintrs = []
    for n in range(1, Num + 1):
        uintr = df['{}-uintr'.format(n)].tolist()
        uintrs.append(uintr)
    return uintrs

def median_index(data):
    n = len(data)
    median_value = sorted(data)[n // 2]  
    median_index = data.index(median_value)
    return median_index


def plot_exe(work):
    plt.figure(figsize=(4.5, 3))
    
    nums = [i for i in range(1, Num+1)]
    nums1 = [i-0.22 for i in range(1, Num+1)]
    nums2 = [i+0.22 for i in range(1, Num+1)]
    simdreg = get_exe(work + '/simdreg/summary.csv')
    custom = get_exe(work + '/custom/summary.csv')
    
    plt.scatter(1-0.22, simdreg[0][0], c=color[0], marker='.', s=3, label='save all')
    plt.scatter(1+0.22, custom[0][0], c=color[1], marker='.', s=3, label='save essentail')
    
    plt.boxplot(simdreg, positions=nums1, showfliers=False, widths=0.4, capprops=dict(linewidth=0.5),whiskerprops=dict(linewidth=0.5), boxprops=dict(linewidth=0.5), medianprops = dict(color = color[0], linewidth = 0.5)) 
    plt.boxplot(custom, positions=nums2, showfliers=False, widths=0.4, capprops=dict(linewidth=0.5),whiskerprops=dict(linewidth=0.5), boxprops=dict(linewidth=0.5), medianprops = dict(color = color[1], linewidth = 0.5))
    # plt.plot(nums, simdreg_m, c=color[0], label='save all', marker='o', markerfacecolor='none')
    # plt.plot(nums, custom_m, c=color[1], label='save essentail', marker='o', markerfacecolor='none')
    
    # for i in range(0, Num):
    #     for e in simdreg[i]:
    #           plt.scatter(i+1, e, c=color[0], marker='o', s=0.1) #, label='save all')

    # for i in range(0, Num):
    #     for e in custom[i]:
    #         plt.scatter(i+1, e, c=color[1], marker='o', s=0.1) # label='save essentail')
    
    plt.legend()
    plt.xticks([1, 4, 8, 12, 16], [1, 4, 8, 12, 16])
    plt.ylim(bottom=0)
    plt.xlabel('Number of uthreads')
    plt.ylabel('Execution time (sec)')
    
    plt.tight_layout()
    plt.savefig(work + '/exe.pdf')
    plt.show()


def plot_overhead(work):
    plt.figure(figsize=(4.5, 3))
    
    nums = [i for i in range(1, Num+1)]
    simdreg_e = get_exe(work + '/simdreg/summary.csv')
    custom_e = get_exe(work + '/custom/summary.csv')
    simdreg_u = get_uintr(work + '/simdreg/summary.csv')
    custom_u = get_uintr(work + '/custom/summary.csv')
    
    o1, o2 = [], []
    for i in range(0, Num):
        idx = median_index(simdreg_e[i])
        e = simdreg_e[i][idx]
        u = simdreg_u[i][idx]
        o1.append((e - (i+1)*baseline) / u * (10**6))
        print(e, baseline, u)
    for i in range(0, Num):
        idx = median_index(custom_e[i])
        e = custom_e[i][idx]
        u = custom_u[i][idx]
        o2.append((e - (i+1)*baseline) / u * (10**6))
    
    plt.plot(nums, o1, c=color[0], label='save all', marker='o', markersize=5, markerfacecolor='none')
    plt.plot(nums, o2, c=color[1], label='save essentail', marker='o', markersize=5, markerfacecolor='none')
    
    plt.legend()
    plt.xticks([1, 4, 8, 12, 16], [1, 4, 8, 12, 16])
    plt.ylim(bottom=0)
    plt.xlabel('Number of uthreads')
    plt.ylabel('Preemption + Switch overhead (us)')
    
    plt.tight_layout()
    plt.savefig(work + '/overhead.pdf')
    plt.show()


def print_overhead(work):    
    nums = [i for i in range(1, Num+1)]
    simdreg_e = get_exe(work + '/simdreg/summary.csv')
    custom_e = get_exe(work + '/custom/summary.csv')
    simdreg_u = get_uintr(work + '/simdreg/summary.csv')
    custom_u = get_uintr(work + '/custom/summary.csv')
    
    for i in range(1, Num):
        idx = median_index(simdreg_e[i])
        e1 = simdreg_e[i][idx]
        u1 = simdreg_u[i][idx]
        
        idx = median_index(custom_e[i])
        e2 = custom_e[i][idx]
        u2 = custom_u[i][idx]
        
        d = (e1 - e2) / u2 * 1e9
        print(f"{i+1} user threads: {d:.1f} ns")

work = sys.argv[1]
# plot_exe(work)
# plot_overhead(work)
print_overhead(work)