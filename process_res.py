# -*- coding: utf-8 -*-
import re
import datetime
import matplotlib.pyplot as plt
import sys
import scipy.stats as stats
import numpy as np
import seaborn as sns
from uuid import UUID

input_file = 'out.txt'
if len(sys.argv) > 1:
    print(sys.argv[1])
    input_file = sys.argv[1]

messages = {}
conversations = {}

with open(input_file, 'r', encoding='utf-8') as infile:
    for line in infile:
        # print(line)
        match = re.search(r"\| (agent.*)", line)
        if match:
            # print(match.group(1))
            rec = match.group(1).split(';')
            if rec[3] not in messages:
                messages[rec[3]] = {'sender': rec[0], 'receiver': rec[1], 'sendtime': rec[6]}
            else:
                messages[rec[3]].update({'receivetime': rec[6]})

            if rec[4] not in conversations:
                conversations[rec[4]] = {'sender': rec[0], 'receiver': rec[1], 'sendtime': rec[6]}
            else:   
                conversations[rec[4]].update({'receivetime': rec[6]})

#print(messages)
#print(conversations)

uuids_with_only_sendtime = [uuid for uuid, details in messages.items() if 'receivetime' not in details]
uuidsconv_with_only_sendtime = [uuid for uuid, details in conversations.items() if 'receivetime' not in details]
# print("UUIDs with only sendtime:", uuids_with_only_sendtime)

for mess in messages:
    if 'receivetime' in messages[mess]:
        xxx = datetime.datetime.strptime(messages[mess]['sendtime'], '%Y-%m-%d %H:%M:%S.%f')
        yyy = datetime.datetime.strptime(messages[mess]['receivetime'], '%Y-%m-%d %H:%M:%S.%f')
        diff = (yyy - xxx).microseconds
        messages[mess].update({'diff': diff})
    else:
        print (messages[mess]['uuid'])

diff_values = [messages[mess]['diff'] for mess in messages if 'diff' in messages[mess]]

print("Processed {} messages, {} conversations".format(len(messages), len(conversations)))
print("diff value[0:10]:", diff_values[0:10])

for conv in conversations:
    if 'receivetime' in conversations[conv]:
        xxx = datetime.datetime.strptime(conversations[conv]['sendtime'], '%Y-%m-%d %H:%M:%S.%f')
        yyy = datetime.datetime.strptime(conversations[conv]['receivetime'], '%Y-%m-%d %H:%M:%S.%f')
        diff = (yyy - xxx).microseconds
        conversations[conv].update({'diff': diff})
    else:
        print (conversations[conv]['uuid'])

diff_conv_values = [conversations[conv]['diff'] for conv in conversations if 'diff' in conversations[conv]]

# Treat diff_values as a normal distribution
mean_diff = np.mean(diff_values)
std_dev_diff = np.std(diff_values)
median_diff = np.median(diff_values)
skewness_diff = stats.skew(diff_values)
kurtosis_diff = stats.kurtosis(diff_values)
stat, p = stats.shapiro(diff_values)

# Save the mean and standard deviation to a text file
output_file = 'stats_{}.txt'.format(input_file)
with open(output_file, 'w') as outfile:
    outfile.write(f"Mean diff: {mean_diff}\n")
    outfile.write(f"Standard deviation of diff: {std_dev_diff}\n")
    outfile.write(f"Median diff: {median_diff}\n")
    outfile.write(f"Skewness of diff: {skewness_diff}\n")
    outfile.write(f"Kurtosis of diff: {kurtosis_diff}\n")
    outfile.write(f"Shapiro-Wilk statistic {stat}: p-value {p}\n")

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
plt.xlabel('Latency (microseconds)')
plt.ylabel('Frequency')

# Add legend
plt.legend()
plt.savefig('histogram{}.png'.format(input_file))
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
plt.savefig('histogram_conversations{}.png'.format(input_file))


