import sys
import re
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import matplotlib
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DF_RESULT_DIR = os.path.join(SCRIPT_DIR, 'results/cost_df')
ROCKSDB_RESULT_DIR = os.path.join(SCRIPT_DIR, 'results/cost_rocksdb')

TRIAL = 99
def get_data(result_dir, quantum, work, mech, all=1):
	res = []
	path = '{}/{}/{}/{}'.format(result_dir, quantum, work, mech) + ('_all' if all == 1 else '')

	for i in range(1, TRIAL+1):
		filename = os.path.join(path, str(i))
		exe, uintr = None, None
		with open(filename, "r") as file:
			for line in file:
				columns = re.split(r'\s+', line)
				if 'Execution:' in columns:
					exe = float(columns[1])
				if 'Preemption_received:' in columns:
					uintr = int(columns[1])
		if exe is not None and uintr is not None:
			res.append([exe, uintr])
	sorted_res = sorted(res, key=lambda x: x[0])
	return sorted_res[len(sorted_res)//2][0], sorted_res[len(sorted_res)//2][1]

def cal_base_exe(result_dir, w, mech):
	if mech == 'signal':
		return get_data(result_dir, 100000000, w, 'signal', all=0)[0]
	else:
		return get_data(result_dir, 100000000, w, 'uintr', all=0)[0]

work = ['scan', 'scan+scan+scan+scan+scan+scan+scan+scan', 
		'get+scan+get+scan+get+scan+get+scan+get+scan+get+scan+get+scan+get+scan+get+scan+get+scan']
work_name = ['scan', 
			r'$\text{scan} \times 8$', 
			r'$\text{get} \times 8+$' '\n' r'$\text{scan} \times 8$']
			# r'$\text{Get} \times 8$' r'$+\text{Scan} \times 8$']

mech = ['signal', 'uintr', 'concord']
mech_name = ['Signals', 'UINTR', 'Compiler']

quantum = 5
data = {}
for m in mech:
	m_ = m + '_all'
	data[m_] = []
	for idx in range(len(work)):
		w = work[idx]
		result_dir = ROCKSDB_RESULT_DIR
		base = cal_base_exe(result_dir, w, m)
		exe, preempt = get_data(result_dir, quantum, w, m, all=1)
		cost = (exe - base) / preempt * (10**6)
		# print('All:', m, w, quantum, f'{cost} = ({exe} - {base}) / {preempt}')
		data[m_].append(cost)
for m in mech:
	data[m] = []
	for idx in range(len(work)):
		w = work[idx]
		result_dir = ROCKSDB_RESULT_DIR
		base = cal_base_exe(result_dir, w, m)
		exe, preempt = get_data(result_dir, quantum, w, m, all=0)
		cost = (exe - base) / preempt * (10**6)
		data[m].append(cost)
		# print('Preempt:', m, w, quantum, cost)

# colors_all = ['#A8DDFE', '#E57373', '#f4a261']
colors_all = ['#D1EDFF', '#F4B6B6', '#FFD4A8']
# colors = ['#56B4E9', '#D62728', 'darkorange']
colors = ['#56B4E9', '#E14A3F', '#FF8C29']



x = np.array([1, 2.2, 3.4])


fig, ax = plt.subplots(figsize=(4.0, 2.3))
bar_width = 0.3 
offset = -0.3

for i in range(len(mech)):
	m = mech[i]
	m_ = m + '_all'
	ax.bar(x + offset + i * bar_width, data[m_], width=bar_width, color=colors_all[i], edgecolor='black', label='{} (context switch)'.format(mech_name[i]))
	for i in range(len(data[m_])):
		print(f'{m}: {data[m_][i] - data[m][i]} = {data[m_][i]} - {data[m][i]}')

for i in range(len(mech)):
	m = mech[i]
	ax.bar(x + offset + i * bar_width, data[m], width=bar_width, color=colors[i], edgecolor='black', label='{} (preemption)'.format(mech_name[i]))
    
ax.set_xticks(x)
ax.set_xticklabels(work_name, fontsize=12)
ax.set_ylabel(r'Average Cost ($\mu{}$s)', fontsize=14)
ax.tick_params(axis='y', labelsize=12)
ax.set_ylim(top=5)
ax.set_xlim(left=0.45, right=3.95)

plt.subplots_adjust(
    left=0.115,   
    right=0.98, 
    bottom=0.19,  
    top=0.95,    
)

# plt.title('DataFrames (5 us)', fontsize=30)
# plt.tight_layout()
plt.savefig('figures/rocksdb_cost.pdf')
plt.show()
