# -*- coding: utf-8 -*-
import re
import datetime
import matplotlib.pyplot as plt

input_file = 'out.txt'

messages = {}

with open(input_file, 'r') as infile:
    for line in infile:
        match = re.search(r"\| (agent.*)", line)
        if match:
            print(match.group(1))
            rec = match.group(1).split(';')
            if rec[2] not in messages:
                messages[rec[2]] = {'sender': rec[0], 'receiver': rec[1], 'sendtime': rec[4]}
            else:
                messages[rec[2]].update({'receivetime': rec[4]})

print(len(messages))

uuids_with_only_sendtime = [uuid for uuid, details in messages.items() if 'receivetime' not in details]
print("UUIDs with only sendtime:", uuids_with_only_sendtime)

for mess in messages:
    if 'receivetime' in messages[mess]:
        xxx = datetime.datetime.strptime(messages[mess]['sendtime'], '%Y-%m-%d %H:%M:%S.%f')
        yyy = datetime.datetime.strptime(messages[mess]['receivetime'], '%Y-%m-%d %H:%M:%S.%f')
        diff = (yyy - xxx).microseconds
        messages[mess].update({'diff': diff})
    else:
        print (messages[mess]['uuid'])

        

diff_values = [messages[mess]['diff'] for mess in messages if 'diff' in messages[mess]]

plt.hist(diff_values, bins=25, edgecolor='black')
plt.title('Histogram of diff values')
plt.xlabel('Diff (microseconds)')
plt.ylabel('Frequency')
plt.show()
