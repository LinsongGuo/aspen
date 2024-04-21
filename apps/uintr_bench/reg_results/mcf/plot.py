import sys
import re
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

color = ['#DADBE7', '#9D9BC3', '#66519D']
trial = 23

def get_data(filename):
	exe, uintr = None, None
	with open(filename, "r") as file:
		for line in file:
			columns = re.split(r'\s+', line)
			if 'Execution:' in columns:
				exe = float(columns[1])
			if 'Preemption_received:' in columns:
				uintr = int(columns[1])
	return exe, uintr

def get_median_index(arr):
    sorted_arr = sorted(arr) 
    median_index = len(arr) // 2  
    if len(arr) % 2 == 0:
        median_index -= 1
    return arr.index(sorted_arr[median_index])

def collect(work_spec, mode):
	exe_, uintr_ = [], []
	trial_ = trial
	if work_spec == 'mcf*2':
		print("mcf*2")
		trial_ = 51
	if  work_spec == 'mcf*8':
		print("mcf*8")
		trial_ = 39
	if  work_spec == 'mcf*20':
		print("mcf*20")
		trial_ = 27
	if  work_spec == 'mcf*24':
		print("mcf*24")
		trial_ = 39
	if  work_spec == 'mcf*28':
		print("mcf*28")
		trial_ = 29
	for i in range(1, trial_+1):
		exe, uintr = get_data('5/{}/{}/{}'.format(work_spec, mode, i))
		if (exe is not None) and (uintr is not None): 
			exe_.append(exe)
			uintr_.append(uintr)
	idx = get_median_index(exe_)
	return exe_[idx], uintr_[idx]

num = [2, 3, 4, 8, 12, 16, 20, 24, 28, 32]
overdiff = []
for n in num:
	work = 'mcf*{}'.format(n)
	save_all = collect(work, 'save_all')
	save_ess = collect(work, 'save_ess')
	res = (save_all[0] - save_ess[0])/save_ess[1]*1e9
	overdiff.append(res)

# print(overdiff)	
plt.figure(figsize=(4, 2.5))
plt.plot(num, overdiff, marker='o', fillstyle='none', linewidth=2, color=color[2])
plt.legend()
plt.xticks([2, 4, 8, 12, 16, 20, 24, 28, 32], [2, 4, 8, 12, 16, 20, 24, 28, 32])
plt.ylabel('Additional overhead of saving \n 256-bits YMM0-YMM31 registers (ns)')
plt.ylim(0,80)
plt.tight_layout()
plt.savefig('add_overhead_mcf.pdf')
plt.show()


# bar_width = 0.2
# X = np.arange(len(work_specs))


# overhead20, overhead10, overhead5 = [], [], []
# for work_spec in work_specs:
# 	base = calc_base(work_spec)
# 	exe, uintr = collect(work_spec)
# 	overhead20.append((exe[0]-base)*1000*1000/uintr[0])
# 	overhead10.append((exe[1]-base)*1000*1000/uintr[1])
# 	overhead5.append((exe[2]-base)*1000*1000/uintr[2])

# plt.figure(figsize=(10, 4))
# plt.bar(X - bar_width, overhead20, width=bar_width, edgecolor='black', linewidth=0.5, label='20 us', color=color[0])
# plt.bar(X, overhead10, width=bar_width, edgecolor='black', linewidth=0.5, label='10 us', color=color[1])
# plt.bar(X + bar_width, overhead5, width=bar_width, edgecolor='black', linewidth=0.5, label='5 us', color=color[2])
# plt.legend() 
# plt.xticks(X, work_specs_shown)
# plt.ylabel('Overhead (us)')
# plt.tight_layout()
# plt.savefig('overhead.pdf')
# plt.show()



# slowdown20, slowdown10, slowdown5 = [], [], []
# for work_spec in work_specs:
# 	base = calc_base(work_spec)
# 	exe, uintr = collect(work_spec)
# 	slowdown20.append((exe[0]/base - 1)*100)
# 	slowdown10.append((exe[1]/base - 1)*100)
# 	slowdown5.append((exe[2]/base - 1)*100)
# plt.figure(figsize=(10, 4))
# plt.bar(X - bar_width, slowdown20, width=bar_width, edgecolor='black', linewidth=0.5, label='20 us', color=color[0])
# plt.bar(X, slowdown10, width=bar_width, edgecolor='black', linewidth=0.5, label='10 us', color=color[1])
# plt.bar(X + bar_width, slowdown5, width=bar_width, edgecolor='black', linewidth=0.5, label='5 us', color=color[2])
# plt.legend()
# plt.xticks(X, work_specs_shown)
# plt.yticks([5, 10, 15, 20], ['5%', '10%', '15%', '20%'])
# plt.ylabel('Slowdown')
# plt.tight_layout()
# plt.savefig('slowdown.pdf')
# plt.show()



