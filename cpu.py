#! /usr/bin/env python

"""
Usage: ./cpu.py config1.json,config2.json,...,configN.json

Determine the CPU model by running under various configuration changes. BaseModel.json and RealisticModel.json
provide defaults and configN.json overrides values in those configs or earlier ones in the list
"""

from __future__ import division
from __future__ import print_function

import sys
import collections
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import json
from configure import configure, run_model, mc_event_model, in_shutdown
from utils import performance_by_year

# Basic parameters
kilo = 1000
mega = 1000 * kilo
giga = 1000 * mega
tera = 1000 * giga
peta = 1000 * tera
seconds_per_year = 86400 * 365
seconds_per_month = 86400 * 30
running_time = 7.8E06

modelNames = None
if len(sys.argv) > 1:
    modelNames = sys.argv[1].split(',')
model = configure(modelNames)

software_improvement_factor = model['improvement_factors']['software']
cpu_improvement_factor = model['improvement_factors']['hardware']
retirement_rate = 0.05

# The very important list of years
YEARS = list(range(model['start_year'], model['end_year']+1))

# Get the performance year by year which includes the software improvement factor
reco_time = {year: performance_by_year(model, year, 'RECO', data_type='data')[0] for year in YEARS}

lhc_sim_time = {year: performance_by_year(model, year, 'GENSIM',
                                              data_type='mc', kind='2017')[0] +
                  performance_by_year(model, year, 'DIGI',
                                          data_type='mc', kind='2017')[0] +
                  performance_by_year(model, year, 'RECO',
                                          data_type='mc', kind='2017')[0] for year in YEARS}

hllhc_sim_time = {year: performance_by_year(model, year, 'GENSIM',
                                            data_type='mc', kind='2026')[0] +
                        performance_by_year(model, year, 'DIGI',
                                            data_type='mc', kind='2026')[0] +
                        performance_by_year(model, year, 'RECO',
                                            data_type='mc', kind='2026')[0] for year in YEARS}

# CPU time requirement calculations, in HS06 * s
# Take the running time and event rate from the model

data_events = {i: run_model(model, i, data_type='data').events for i in YEARS}

lhc_mc_events = {i: mc_event_model(model, i)['2017'] for i in YEARS}
hllhc_mc_events = {i: mc_event_model(model, i)['2026'] for i in YEARS}

data_cpu_time = {i : data_events[i] * reco_time[i] for i in YEARS}

lhc_mc_cpu_time = {i : lhc_mc_events[i] * lhc_sim_time[i] for i in YEARS}
hllhc_mc_cpu_time = {i : hllhc_mc_events[i] * hllhc_sim_time[i] for i in YEARS}

# The data need to be reconstructed about as quickly as we record them.  In
# addition, we need to factor in express, repacking, AlCa, CAF
# functionality and skimming.  Presumably these all scale like the data.
# Per the latest CRSG document, these total to 123 kHS06 compared to 240
# kHS016 for the prompt reconstruction, which we can round to 50%, so
# multiply by 50%.  (Ignoring the 10 kHS06 needed for VO boxes, which
# won't scale up and is also pretty small.)  In-year reprocessing model:
# assume we will re-reco 10% of the data each year, but we want to
# complete it in one month.


data_cpu_required = {i : (1.5 * data_cpu_time[i] / running_time
                              + 0.1 * data_cpu_time[i] / seconds_per_month)
                         for i in YEARS}

# Also keep using the _time variables to sum up the total HS06 * s needed,
# which frees us from assumptions on time needed to complete the work.

data_cpu_time = {i : 1.6 * data_cpu_time[i] for i in YEARS}
    
# The corresponding MC, on the other hand, can be reconstructed over an
# entire year.  We can use this to calculate the HS06 needed to do those
# tasks.

lhc_mc_cpu_required = {i : lhc_mc_cpu_time[i] / seconds_per_year for i in YEARS}
hllhc_mc_cpu_required = {i : hllhc_mc_cpu_time[i] / seconds_per_year for i in YEARS}

# Unless it is a year with new detectors in, in which case we will have
# less time to make MC (say half as much).  Only applies to the current
# era, i.e. no need to compress HL-LHC MC when we are still in LHC era.

for i in YEARS:
    if (i in model['new_detector_years']):
        if i < 2026:
            lhc_mc_cpu_required[i] = lhc_mc_cpu_time[i]/ (seconds_per_year / 2)
        else:
            hllhc_mc_cpu_required[i] = hllhc_mc_cpu_time[i]/ (seconds_per_year / 2)
            

# Analysis!  In the current resource request, the amount requested for
# analysis is within 10% of the total CPU for prompt reco plus MC at T1 and T2.  So, just set analysis equal to data + mc above.

analysis_cpu_required = {i : lhc_mc_cpu_required[i] + hllhc_mc_cpu_required[i] + data_cpu_required[i] for i in YEARS}

analysis_cpu_time = {i : data_cpu_time[i] + lhc_mc_cpu_time[i] +
                         hllhc_mc_cpu_time[i] for i in YEARS}

# Shutdown year model:

# If in the first year of a shutdown, need to reconstruct the previous
# three years of data, but you have all year to do it.  No need for all the
# ancillary stuff.

for i in YEARS:
    shutdown_this_year, dummy = in_shutdown(model,i)
    shutdown_last_year, dummy = in_shutdown(model,i-1)
    if (shutdown_this_year and not(shutdown_last_year)):
        data_events[i] = 3 * data_events[i-1] 
        data_cpu_time[i] = 3 * data_events[i] * reco_time[i]
        data_cpu_required[i] = data_cpu_time[i] / seconds_per_year
        
# But we still do analysis in years where we don't record data.  Set
# analysis for that year equal to the most recent running year.

for i in YEARS:
    if analysis_cpu_required[i] == 0:
        analysis_cpu_required[i] = analysis_cpu_required[i-1]
        analysis_cpu_time[i] = analysis_cpu_time[i-1]
        
# Sum up everything
        
total_cpu_required = {i : data_cpu_required[i] + lhc_mc_cpu_required[i] +
                          hllhc_mc_cpu_required[i] +
                          analysis_cpu_required[i] for i in YEARS}

total_cpu_time = {i: data_cpu_time[i] + lhc_mc_cpu_time[i] +
                      hllhc_mc_cpu_time[i] + analysis_cpu_time[i]
                      for i in YEARS}
    
# Then, CPU availability calculations.  This follows the "Available CPU
# power" spreadsheet.  Take a baseline value of 1.4 MHS06 in 2016, in
# future years subtract 5% of the previous for retirements, and add 300
# kHS06 which gets improved by the cpu_improvement in each year, until
# 2020, during LS2, when we shift the computing model to start buying an
# improved 600 kHS06 per year.

# This is kludgey -- need to establish the baseline to make the
# caluculation work, but once the calculation is there, delete the baseline
# for the histogram to work.  Not to mention that I couldn't get the
# dictionary comprehension to work here.

cpu_improvement = {i : cpu_improvement_factor ** (i-2017) for i in YEARS}

cpu_capacity = {2016 : 1.4 * mega}

# This variable assumes that you can have the cpu_capacity for an entire
# year and thus calculates the HS06 * s available (in principle).

cpu_time_capacity = {2016 : 1.4 * mega * seconds_per_year}

for i in YEARS:
    cpu_capacity[i] = cpu_capacity[i-1] * (1 - retirement_rate) + (300 if i < 2020 else 600) * kilo * cpu_improvement[i]
    cpu_time_capacity[i] = cpu_capacity[i] * seconds_per_year
    
del cpu_capacity[2016]
del cpu_time_capacity[2016]    

# CPU capacity model ala data.py

# Set the initial points
cpuCapacity = {str(model['capacity_model']['cpu_year']): model['capacity_model']['cpu_start']}
cpuTimeCapacity = {str(model['capacity_model']['cpu_year']): model['capacity_model']['cpu_start']*seconds_per_year}


# A bit of a kludge. Assume what we have now was bought and will be retired in equal chunks over its lifetime
cpuAdded = {}
for year in range(model['capacity_model']['cpu_year'] - model['capacity_model']['cpu_lifetime'] + 1,
                  model['capacity_model']['cpu_year'] + 1):
    retired = model['capacity_model']['cpu_start'] / model['capacity_model']['cpu_lifetime']
    cpuAdded[str(year)] = retired

cpuFactor = model['improvement_factors']['hardware']

for year in YEARS:
    if str(year) not in cpuCapacity:
        cpuDelta = 0  # Find the delta which can be time dependant
        cpuDeltas = model['capacity_model']['cpu_delta']
        for deltaYear in sorted(cpuDeltas.keys()):
            if int(year) >= int(deltaYear):
                lastCpuYear = int(deltaYear)
                cpuDelta = model['capacity_model']['cpu_delta'][deltaYear]
                
        cpuAdded[str(year)] = cpuDelta * cpuFactor ** (int(year) - int(lastCpuYear))

        # Retire cpu added N years ago or retire 0

        cpuRetired = cpuAdded.get(str(int(year) - model['capacity_model']['cpu_lifetime']), 0)
        cpuCapacity[str(year)] = cpuCapacity[str(int(year) - 1)] + cpuAdded[str(year)] - cpuRetired
        cpuTimeCapacity[str(year)] = cpuCapacity[str(year)] * seconds_per_year

print("CPU requirements in HS06")
for i in YEARS:
    print(i, '{:04.3f}'.format(data_cpu_required[i] / mega),
    '{:04.3f}'.format(lhc_mc_cpu_required[i] / mega),
    '{:04.3f}'.format(hllhc_mc_cpu_required[i] / mega),
    '{:04.3f}'.format(analysis_cpu_required[i] / mega),
    '{:04.3f}'.format(total_cpu_required[i] / mega),
    '{:04.3f}'.format(cpu_capacity[i] / mega), 
    '{:04.3f}'.format(cpuCapacity[str(i)] / mega), 'MHS06',
    '{:04.3f}'.format(total_cpu_required[i]/cpuCapacity[str(i)])
              )
print("CPU requirements in HS06 * s")
for i in YEARS:
    print(i, '{:04.3f}'.format(data_cpu_time[i] / tera),
    '{:04.3f}'.format(lhc_mc_cpu_time[i] / tera),
    '{:04.3f}'.format(hllhc_mc_cpu_time[i] / tera),
    '{:04.3f}'.format(analysis_cpu_time[i] / tera),
    '{:04.3f}'.format(total_cpu_time[i] / tera),
    '{:04.3f}'.format(cpu_time_capacity[i] / tera), 
    '{:04.3f}'.format(cpuTimeCapacity[str(i)] / tera), 'THS06 * s',
    '{:04.3f}'.format(total_cpu_time[i]/cpuTimeCapacity[str(i)])
              )

    
# Plot the HS06

# Squirt the dictionary entries into lists:

cpuDataList = []
for year, item in sorted(data_cpu_required.items()):
    cpuDataList.append(item/mega)
cpuLHCMCList = []
for year, item in sorted(lhc_mc_cpu_required.items()):
    cpuLHCMCList.append(item/mega)
cpuHLLHCMCList = []
for year, item in sorted(hllhc_mc_cpu_required.items()):
    cpuHLLHCMCList.append(item/mega)
cpuAnaList = []
for year, item in sorted(analysis_cpu_required.items()):
    cpuAnaList.append(item/mega)
cpuCapacityList = []
for year, item in sorted(cpu_capacity.items()):
    cpuCapacityList.append(item/mega)
altCapacityList = []
for year, item in sorted(cpuCapacity.items()):
    altCapacityList.append(item/mega)
    
# Build a data frame from lists:

cpuFrame = pd.DataFrame({'Year': [str(year) for year in YEARS],
                             'Data' : cpuDataList,
                             'LHC MC' : cpuLHCMCList,
                             'HL-LHC MC' : cpuHLLHCMCList,
                             'Analysis' : cpuAnaList,
                             'Capacity, 5% retirement' : cpuCapacityList,
                             'Capacity, 5 year retirement' : altCapacityList}
                            )


ax = cpuFrame[['Year','Capacity, 5% retirement']].plot(x='Year',linestyle='-',marker='o', color='Red')
cpuFrame[['Year','Capacity, 5 year retirement']].plot(x='Year',linestyle='-',marker='o', color='Blue',ax=ax)
cpuFrame[['Year', 'Data', 'LHC MC', 'HL-LHC MC', 'Analysis']].plot(x='Year',kind='bar',stacked=True,ax=ax)
ax.set(ylabel='MHS06')
ax.set(title='CPU improvement %s Software improvement = %s' %
           (cpu_improvement_factor, software_improvement_factor))

fig = ax.get_figure()
fig.savefig('CPU by Type.png')

# Do the same thing for the HS06 * s

# Squirt the dictionary entries into lists:

cpuDataTimeList = []
for year, item in sorted(data_cpu_time.items()):
    cpuDataTimeList.append(item/tera)
cpuLHCMCTimeList = []
for year, item in sorted(lhc_mc_cpu_time.items()):
    cpuLHCMCTimeList.append(item/tera)
cpuHLLHCMCTimeList = []
for year, item in sorted(hllhc_mc_cpu_time.items()):
    cpuHLLHCMCTimeList.append(item/tera)
cpuAnaTimeList = []
for year, item in sorted(analysis_cpu_time.items()):
    cpuAnaTimeList.append(item/tera)
cpuCapacityTimeList = []
for year, item in sorted(cpu_time_capacity.items()):
    cpuCapacityTimeList.append(item/tera)
altCapacityTimeList = []
for year, item in sorted(cpuTimeCapacity.items()):
    altCapacityTimeList.append(item/tera)
    
# Build a data frame from lists:

cpuTimeFrame = pd.DataFrame({'Year': [str(year) for year in YEARS],
                             'Data' : cpuDataTimeList,
                             'LHC MC' : cpuLHCMCTimeList,
                             'HL-LHC MC' : cpuHLLHCMCTimeList,
                             'Analysis' : cpuAnaTimeList,
                             'Capacity, 5% retirement' : cpuCapacityTimeList,
                             'Capacity, 5 year retirement' : altCapacityTimeList}
                            )


ax = cpuTimeFrame[['Year','Capacity, 5% retirement']].plot(x='Year',linestyle='-',marker='o', color='Red')
cpuTimeFrame[['Year','Capacity, 5 year retirement']].plot(x='Year',linestyle='-',marker='o', color='Blue',ax=ax)
cpuTimeFrame[['Year', 'Data', 'LHC MC', 'HL-LHC MC', 'Analysis']].plot(x='Year',kind='bar',stacked=True,ax=ax)
ax.set(ylabel='THS06 * s')
ax.set(title='CPU improvement %s Software improvement = %s' %
           (cpu_improvement_factor, software_improvement_factor))

fig = ax.get_figure()
fig.savefig('CPU seconds by Type.png')


