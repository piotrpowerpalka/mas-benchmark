# -*- coding: utf-8 -*-
import re
import datetime
import matplotlib.pyplot as plt
import sys
import os
import scipy.stats as stats
import numpy as np
import seaborn as sns
from uuid import UUID
import pandas as pd


input_file = 'out.txt'
if len(sys.argv) > 1:
    print(sys.argv[1])
    input_file = sys.argv[1]

input_name = os.path.basename(input_file)

messages = {}
conversations = {}
inits = []

with open(input_file, 'r', encoding='utf-8') as infile:
    for line in infile:
        # print(line)
        matchinit = re.search(r"\| (init;.*)", line)
        match = re.search(r"\| (agent.*)", line)
        if matchinit:
            rec = matchinit.group(1).split(';')
            if len(rec) == 4 and rec[1] in ("initializing", "running"):
                inits.append(rec[3])

        if match:
            # print(match.group(1))
            rec = match.group(1).split(';')
            if not (re.fullmatch(r"agent\d+", rec[0]) and re.fullmatch(r"agent\d+", rec[1])):
                continue

            message = messages.setdefault(rec[3], {})
            conversation = conversations.setdefault(rec[4], {})
            if rec[5] == "S":
                message.update({'sender': rec[0], 'receiver': rec[1], 'sendtime': rec[6]})
                conversation.update({'sender': rec[0], 'receiver': rec[1], 'sendtime': rec[6]})
            elif rec[5] == "R":
                message.update({'receivetime': rec[6]})
                conversation.update({'receivetime': rec[6]})

if not inits:
    raise ValueError("No initialization timestamps found in {}".format(input_file))

init_start = min(inits, key=pd.Timestamp)
init_end = max(inits, key=pd.Timestamp)
initTime = (pd.Timestamp(init_end) - pd.Timestamp(init_start)).total_seconds()

#print(messages)
#print(conversations)

uuids_with_only_sendtime = [uuid for uuid, details in messages.items() if 'sendtime' in details and 'receivetime' not in details]
uuidsconv_with_only_sendtime = [uuid for uuid, details in conversations.items() if 'sendtime' in details and 'receivetime' not in details]
# print("UUIDs with only sendtime:", uuids_with_only_sendtime)

for mess in messages:
    if 'sendtime' in messages[mess] and 'receivetime' in messages[mess]:
        sendtime = messages[mess]['sendtime']
        rectime  = messages[mess]['receivetime']
        xxx = pd.Timestamp(sendtime)
        yyy = pd.Timestamp(rectime)       
        diff: pd.Timedelta = yyy - xxx
        messages[mess].update({'diff': diff.total_seconds()})  # Convert to seconds

    elif 'sendtime' in messages[mess]:
        print (messages[mess])  

diff_values = [messages[mess]['diff'] for mess in messages if 'diff' in messages[mess]]

print("Processed {} messages, {} conversations".format(len(messages), len(conversations)))
print("diff value[0:10]:", diff_values[0:10])

for conv in conversations:
    if 'sendtime' in conversations[conv] and 'receivetime' in conversations[conv]:
        sendtime = conversations[conv]['sendtime']
        rectime  = conversations[conv]['receivetime']
        xxx = pd.Timestamp(sendtime)
        yyy = pd.Timestamp(rectime)       
        diff: pd.Timedelta = yyy - xxx
        conversations[conv].update({'diff': diff.total_seconds()})  # Convert to seconds
    elif 'sendtime' in conversations[conv]:
        print (conversations[conv])

diff_conv_values = [conversations[conv]['diff'] for conv in conversations if 'diff' in conversations[conv]]

# Treat diff_values as a normal distribution
mean_diff = np.mean(diff_values)
std_dev_diff = np.std(diff_values)
median_diff = np.median(diff_values)
skewness_diff = stats.skew(diff_values)
kurtosis_diff = stats.kurtosis(diff_values)
stat, p = stats.shapiro(diff_values)

mean_conv_diff = np.mean(diff_conv_values)
std_dev_conv_diff = np.std(diff_conv_values)



#inits = [pd.Timestamp(t) for t in inits]
#inits = [t - min(inits) for t in inits]

# Save the mean and standard deviation to a text file
output_file = 'stats_{}.txt'.format(input_name)
with open(output_file, 'w') as outfile:
    outfile.write(f"Initialization started at: {init_start}\n")
    outfile.write(f"Initialization ended at: {init_end}\n")
    outfile.write(f"Initialization duration: {initTime} seconds\n")
    #outfile.write(f"Duration of initialization: {np.max(inits)}\n")

    outfile.write(f"Mean diff: {mean_diff}\n")
    outfile.write(f"Standard deviation of diff: {std_dev_diff}\n")
    outfile.write(f"Median diff: {median_diff}\n")
    outfile.write(f"Skewness of diff: {skewness_diff}\n")
    outfile.write(f"Kurtosis of diff: {kurtosis_diff}\n")
    outfile.write(f"Shapiro-Wilk statistic {stat}: p-value {p}\n")
    
    outfile.write(f"Mean conversation diff: {mean_conv_diff}\n")
    outfile.write(f"Standard deviation of conversation diff: {std_dev_conv_diff}\n")

    # Find the latest timestamp (simulation end time)
    all_times = []
    for mess in messages:
        if 'receivetime' in messages[mess]:
            all_times.append(messages[mess]['receivetime'])
    for conv in conversations:
        if 'receivetime' in conversations[conv]:
            all_times.append(conversations[conv]['receivetime'])

    if all_times:
        
        earliest_time_str = min(all_times)
        earliest_time = pd.Timestamp(earliest_time_str)
        timestamp_start = earliest_time.timestamp()
        latest_time_str = max(all_times)
        latest_time = pd.Timestamp(latest_time_str)
        timestamp = latest_time.timestamp()

        simDur = (latest_time - earliest_time).total_seconds()
        
        outfile.write(f"Simulation started: {earliest_time_str}\n")
        outfile.write(f"Simulation started (timestamp): {timestamp_start}\n")
        outfile.write(f"Simulation ended: {latest_time_str}\n")
        outfile.write(f"Simulation ended (timestamp): {timestamp}\n")
        outfile.write(f"Simulation duration: {simDur} seconds\n")

    outfile.write(f"Messages lost: {len(uuids_with_only_sendtime)}\n")
    outfile.write(f"Conversations lost: {len(uuidsconv_with_only_sendtime)}\n")
    outfile.write(f"Messages successful: {len(diff_values)}\n")
    outfile.write(f"Conversations successful: {len(diff_conv_values)}\n")


    outfile.write(f"{initTime};{simDur};{mean_diff};{median_diff};{std_dev_diff};{stat};;;;{len(uuids_with_only_sendtime)};{len(diff_values)}\n")
    outfile.write(f"{mean_conv_diff};{std_dev_conv_diff}\n")

sns.histplot(diff_values, kde=True, label='Empirical Data', stat="density")

# Generate x values for the normal distribution
x = np.linspace(min(diff_values), max(diff_values), 1000)
# Calculate the normal distribution using the mean and standard deviation
normal_dist = stats.norm.pdf(x, mean_diff, std_dev_diff)
# Scale the normal distribution to match the histogram
normal_dist_scaled = normal_dist * len(diff_values) * (x[1] - x[0])

# Plot the normal distribution
plt.plot(x, normal_dist, label='Normal Distribution', color='red')
plt.title('Histogram of Message Latency')
plt.xlabel('Latency [s]')
plt.ylabel('Frequency')

# Add legend
plt.legend()
plt.savefig('histogram{}.png'.format(input_name))
plt.clf()

sns.histplot(diff_conv_values, kde=True, label='Conversations Data', stat="density", color='orange')
# Generate x values for the normal distribution
x_conv = np.linspace(min(diff_conv_values), max(diff_conv_values), 1000)
# Calculate the normal distribution using the mean and standard deviation
normal_conv_dist = stats.norm.pdf(x_conv, np.mean(diff_conv_values), np.std(diff_conv_values))  
# Scale the normal distribution to match the histogram
normal_conv_dist_scaled = normal_conv_dist * len(diff_conv_values) * (x_conv[1] - x_conv[0])        
# Plot the normal distribution
plt.plot(x_conv, normal_conv_dist, label='Normal Distribution (Conversations)', color='green')
plt.title('Histogram of Conversation Latency')
plt.xlabel('Latency (microseconds)')
plt.ylabel('Frequency')
# Add legend
plt.legend()
plt.savefig('histogram_conversations{}.png'.format(input_name))


