import sys
import re
import os
import pandas as pd

bench = sys.argv[1]
times = int(sys.argv[2])
T = [100000000, 100, 50, 20, 10, 5, 3]
trial = 1

data = {"Trial": [i for i in range(1, trial+1)]}
data["Trial"].append("median")

def get_data(bench, work, t):
    exe, p = [], []
    for i in range(1, trial+1):
        filename = '{}/{}/{}/{}'.format(bench, work, t, i)
        with open(filename, "r") as file:
            for line in file:
                columns = re.split(r'\s+', line)
                if 'Execution:' in columns:
                    exe.append(float(columns[1]))
                if 'Preemption_received:' in columns:
                    p.append(int(columns[1]))      
    return exe, p

def get_median_index(arr):
    sorted_arr = sorted(arr) 
    median_index = len(arr) // 2  
    if len(arr) % 2 == 0:
        median_index -= 1
    return arr.index(sorted_arr[median_index])

for i in range(1, times + 1):
    work = '{}*{}'.format(bench, i)
    for t in T:
        exe, p = get_data(bench, work, t)
        idx = get_median_index(exe)
        exe.append(exe[idx])
        p.append(p[idx])
        data[str(t) + ':exe'] = exe
        data[str(t) + ':preempt'] = p
    df = pd.DataFrame(data)
    df.to_csv('{}/{}/result.csv'.format(bench, work), index=False)