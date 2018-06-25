#! /usr/bin/env python

"""
Usage: ./cpu.py config1.json,config2.json,...,configN.json

Determine the CPU model by running under various configuration changes. BaseModel.json and RealisticModel.json
provide defaults and configN.json overrides values in those configs or earlier ones in the list
"""


from __future__ import division
from __future__ import print_function

import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from CPUModel import CPUModel, mega, tera

modelNames = None
if len(sys.argv) > 1:
    modelNames=[]
    for a in sys.argv[1:]:
        modelNames = modelNames+ a.split(',')
cm = CPUModel(modelNames)

print("Year / Reco / LHC SIM / HLLHC SIM times")
for year in cm.years:
    print(year, int(cm.reco_time[year]), 
          int(cm.lhc_sim_time[year]), int(cm.hllhc_sim_time[year]))
print()
print("Using %s analysis method" % cm.analysis_method)

print("CPU requirements in HS06")
print("Year Prompt NonPrompt LHCMC HLLHCMC Ana Total Cap1 Cap2 Ratio USCMS HPC")
for i in cm.years:
    print(i, '{:04.3f}'.format(cm.data_cpu_required[i] / mega),
    '{:04.3f}'.format(cm.rereco_cpu_required[i] / mega),
    '{:04.3f}'.format(cm.lhc_mc_cpu_required[i] / mega),
    '{:04.3f}'.format(cm.hllhc_mc_cpu_required[i] / mega),
    '{:04.3f}'.format(cm.analysis_cpu_required[i] / mega),
    '{:04.3f}'.format(cm.total_cpu_required[i] / mega),
    '{:04.3f}'.format(cm.cpu_capacity_simple[i] / mega),
    '{:04.3f}'.format(cm.cpu_capacity[str(i)] / mega), 'MHS06',
    '{:04.3f}'.format(cm.total_cpu_required[i]/cm.cpu_capacity[str(i)]),
    '{:04.3f}'.format(0.4* (cm.total_cpu_required[i]) / mega),
    '{:04.3f}'.format(cm.hpc_cpu_required[i]/cm.total_cpu_required[i])
              )

print("CPU requirements in HS06 * s")
print("Year Prompt NonPrompt LHCMC HLLHCMC Ana Total Cap1 Cap2 Ratio USCMS HPC")
for i in cm.years:
    print(i, '{:03.2f}'.format(cm.data_cpu_time[i] / tera),
    '{:03.2f}'.format(cm.rereco_cpu_time[i] / tera),
    '{:03.2f}'.format(cm.lhc_mc_cpu_time[i] / tera),
    '{:03.2f}'.format(cm.hllhc_mc_cpu_time[i] / tera),
    '{:03.2f}'.format(cm.analysis_cpu_time[i] / tera),
    '{:03.2f}'.format(cm.total_cpu_time[i] / tera),
    '{:03.2f}'.format(cm.cpu_time_capacity_simple[i] / tera),
    '{:03.2f}'.format(cm.cpu_time_capacity[str(i)] / tera), 'THS06 * s',
    '{:03.2f}'.format(cm.total_cpu_time[i] / cm.cpu_time_capacity[str(i)]),
    '{:03.2f}'.format(0.4* (cm.total_cpu_time[i]) / tera),
    '{:03.2f}'.format(cm.hpc_cpu_time[i]/cm.total_cpu_time[i])
              )

print("Fraction of CPU required for T1/T2 activities")
print("Year\t Prmpt\t Rreco\tGen\tSim\tSimReco\t Anal\t USCPU")

for i in cm.years:
    print(i,'\t',
    '{:04.3f}'.format(cm.fractions['PROMPT']),'\t',
    '{:04.3f}'.format(cm.fractions['RERECO'][i]),'\t',
    '{:04.3f}'.format(cm.fractions['GEN']),'\t',
    '{:04.3f}'.format(cm.fractions['SIM'][i]),'\t',
    '{:04.3f}'.format(cm.fractions['DIGI'][i] + cm.fractions['RECO'][i]),'\t',
    '{:04.3f}'.format(cm.fractions['ANALYSIS'][i]),'\t',
    '{:04.2f}'.format(cm.uscpu[i]),'\t'
    )

# Plot the HS06

# Squirt the dictionary entries into lists:

cpuDataList = []
for year, item in sorted(cm.data_cpu_required.items()):
    cpuDataList.append(item/mega)
cpuRerecoList = []
for year, item in sorted(cm.rereco_cpu_required.items()):
    cpuRerecoList.append(item/mega)
cpuLHCMCList = []
for year, item in sorted(cm.lhc_mc_cpu_required.items()):
    cpuLHCMCList.append(item/mega)
cpuHLLHCMCList = []
for year, item in sorted(cm.hllhc_mc_cpu_required.items()):
    cpuHLLHCMCList.append(item/mega)
cpuAnaList = []
for year, item in sorted(cm.analysis_cpu_required.items()):
    cpuAnaList.append(item/mega)
cm.cpu_capacityList = []
for year, item in sorted(cm.cpu_capacity_simple.items()):
    cm.cpu_capacityList.append(item/mega)
altCapacityList = []
print (cm.cpu_capacity_simple)
print (cm.cpu_capacity)
for year, item in sorted(cm.cpu_capacity.items()):
    if int(year) in cm.cpu_capacity_simple:
        altCapacityList.append(item/mega)

# Build a data frame from lists:
pngKeyName = ''
if modelNames is not None:
    for m in modelNames:
        pngKeyName = pngKeyName + '_' + m.split('/')[-1].split('.')[0]

plotMaxs = cm.model['plotMaximums']

cpuFrame = pd.DataFrame({'Year': [str(year) for year in cm.years],
                             'Prompt Data' : cpuDataList,
                             'Non-Prompt Data' : cpuRerecoList,
                             'LHC MC' : cpuLHCMCList,
                             'HL-LHC MC' : cpuHLLHCMCList,
                             'Analysis' : cpuAnaList}
                            )


ax = cpuFrame[['Year', 'Prompt Data', 'Non-Prompt Data', 'LHC MC', 'HL-LHC MC',
                   'Analysis']].plot(x='Year', kind='bar', stacked=True, colormap='Paired')
ax.set(ylabel='MHS06')
ax.set(title='CPU by Type')

handles, labels = ax.get_legend_handles_labels()
handles = handles[::-1]
labels = labels[::-1]
ax.legend(handles,labels,loc='best', markerscale=0.25, fontsize=11)
ax.set_ylim(ymax = plotMaxs['CPUByType'])
minYearVal = max(0, cm.model['minYearToPlot'] - cm.years[0]) - 0.5 #pandas...

ax.set_xlim(xmin=minYearVal)
fig = ax.get_figure()
fig.tight_layout()
fig.savefig('CPUByType'+pngKeyName+'.png')

cm.cpu_capacityFrame = pd.DataFrame({'Year': [str(year) for year in cm.years],
                             'Prompt Data' : cpuDataList,
                             'Non-Prompt Data' : cpuRerecoList,
                             'LHC MC' : cpuLHCMCList,
                             'HL-LHC MC' : cpuHLLHCMCList,
                             'Analysis' : cpuAnaList,
                             'Capacity, 5% retirement' : cm.cpu_capacityList,
                             'Capacity, 5 year retirement' : altCapacityList}
                            )


ax = cm.cpu_capacityFrame[['Year','Capacity, 5% retirement']].plot(x='Year',linestyle='-',marker='o', color='Red')
cm.cpu_capacityFrame[['Year','Capacity, 5 year retirement']].plot(x='Year',linestyle='-',marker='o', color='Blue',ax=ax)
cm.cpu_capacityFrame[['Year', 'Prompt Data', 'Non-Prompt Data', 'LHC MC',
                      'HL-LHC MC', 'Analysis']].plot(x='Year', kind='bar', stacked=True, ax=ax, colormap='Paired')
ax.set(ylabel='MHS06')
ax.set(title='CPU by Type and Capacity')
ax.set_ylim(ymax=plotMaxs['CPUByTypeAndCapacity'])
ax.set_xlim(xmin=minYearVal)
handles, labels = ax.get_legend_handles_labels()
handles=handles[::-1]
labels=labels[::-1]
ax.legend(handles, labels, loc='best', markerscale=0.25, fontsize=11)

fig = ax.get_figure()
fig.tight_layout()
fig.savefig('CPUByTypeAndCapacity' + pngKeyName + '.png')


# Do the same thing for the HS06 * d

# Squirt the dictionary entries into lists:

cpuDataTimeList = []
for year, item in sorted(cm.data_cpu_time.items()):
    cpuDataTimeList.append(item/tera)
cpuRerecoTimeList = []
for year, item in sorted(cm.rereco_cpu_time.items()):
    cpuRerecoTimeList.append(item/tera)
cpuLHCMCTimeList = []
for year, item in sorted(cm.lhc_mc_cpu_time.items()):
    cpuLHCMCTimeList.append(item/tera)
cpuHLLHCMCTimeList = []
for year, item in sorted(cm.hllhc_mc_cpu_time.items()):
    cpuHLLHCMCTimeList.append(item/tera)
cpuAnaTimeList = []
for year, item in sorted(cm.analysis_cpu_time.items()):
    cpuAnaTimeList.append(item/tera)
cm.cpu_capacityTimeList = []
for year, item in sorted(cm.cpu_time_capacity_simple.items()):
    cm.cpu_capacityTimeList.append(item/tera)
altCapacityTimeList = []
for year, item in sorted(cm.cpu_time_capacity.items()):
    if int(year) in cm.cpu_time_capacity_simple:
        altCapacityTimeList.append(item/tera)

# Build a data frame from lists:

cpuTimeFrame = pd.DataFrame({'Year': [str(year) for year in cm.years],
                             'Prompt Data' : cpuDataTimeList,
                             'Non-Prompt Data' : cpuRerecoTimeList,
                             'LHC MC' : cpuLHCMCTimeList,
                             'HL-LHC MC' : cpuHLLHCMCTimeList,
                             'Analysis' : cpuAnaTimeList}
                            )


ax = cpuTimeFrame[['Year', 'Prompt Data', 'Non-Prompt Data', 'LHC MC',
                  'HL-LHC MC', 'Analysis']].plot(x='Year', kind='bar', stacked=True, colormap='Paired')
ax.set(ylabel='THS06 * s')
ax.set(title='CPU seconds by Type')
ax.set_ylim(ymax=plotMaxs['CPUSecondsByType'])
ax.set_xlim(xmin=minYearVal)

handles, labels = ax.get_legend_handles_labels()
handles = handles[::-1]
labels = labels[::-1]
ax.legend(handles, labels, loc='best', markerscale=0.25, fontsize=11)

fig = ax.get_figure()
fig.tight_layout()
fig.savefig('CPUSecondsByType' + pngKeyName + '.png')

cm.cpu_time_capacityFrame = pd.DataFrame({'Year': [str(year) for year in cm.years],
                                'Prompt Data' : cpuDataTimeList,
                                'Non-Prompt Data' : cpuRerecoTimeList,
                                'LHC MC' : cpuLHCMCTimeList,
                                'HL-LHC MC' : cpuHLLHCMCTimeList,
                                'Analysis' : cpuAnaTimeList,
                                'Capacity, 5% retirement' : cm.cpu_capacityTimeList,
                                    'Capacity, 5 year retirement' : altCapacityTimeList}
                                )


ax = cm.cpu_time_capacityFrame[['Year','Capacity, 5% retirement']].plot(x='Year',linestyle='-',marker='o', color='Red')
cm.cpu_time_capacityFrame[['Year','Capacity, 5 year retirement']].plot(x='Year',linestyle='-',marker='o', color='Blue',ax=ax)
cm.cpu_time_capacityFrame[['Year', 'Prompt Data', 'Non-Prompt Data', 'LHC MC', 'HL-LHC MC',
                          'Analysis']].plot(x='Year', kind='bar', stacked=True, ax=ax, colormap='Paired')
ax.set(ylabel='THS06 * s')
ax.set(title='CPU seconds by Type and Capacity')
ax.set_ylim(ymax=plotMaxs['CPUSecondsByTypeAndCapacity'])
ax.set_xlim(xmin=minYearVal)

handles, labels = ax.get_legend_handles_labels()
handles = handles[::-1]
labels = labels[::-1]
ax.legend(handles,labels,loc='best', markerscale=0.25, fontsize=11)

fig = ax.get_figure()
fig.tight_layout()
fig.savefig('CPUSecondsByTypeAndCapacity' + pngKeyName + '.png')

