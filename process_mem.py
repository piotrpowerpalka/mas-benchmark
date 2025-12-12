import pandas as pd
import matplotlib.pyplot as plt
import sys

endofsim = -1

input_file = 'data_mem.csv'
if len(sys.argv) > 1:
    print(sys.argv[1])
    input_file = sys.argv[1]

if len(sys.argv) > 2:
    endofsim = sys.argv[2]

df = pd.read_csv(input_file, sep=';', names=['timestamp', 'container', 'memory used / total memory', 'processor usage'])

# Parse memory usage (extract numeric value from "32.86MiB / 512MiB")
df['memory_used'] = df['memory used / total memory'].str.extract(r'(\d+\.?\d*)')[0].astype(float)

# Parse CPU usage (remove % and convert to float)
df['cpu_usage'] = df['processor usage'].str.rstrip('%').astype(float)

# Convert timestamp to datetime
df['time'] = pd.to_datetime(df['timestamp'], unit='s')
df['time'] = df['time'] - df['time'].min()  # Normalize time to start from zero
df['time'] = df['time'].dt.total_seconds()

if (endofsim != -1):
    df = df[df['timestamp'] <= float(endofsim)] # remove all entries after end of simulation

# Calculate statistics
avg_memory = df['memory_used'].mean()
max_memory = df['memory_used'].max()
duration = df['timestamp'].max() - df['timestamp'].min()
cpu_95_percentile = df['cpu_usage'].quantile(0.95)

output_file = 'mem_stats_{}.txt'.format(input_file)
with open(output_file, 'w') as outfile:
    outfile.write(f"Average memory usage: {avg_memory:.2f} MiB")
    outfile.write(f"Maximum memory usage: {max_memory:.2f} MiB")
    outfile.write(f"Experiment duration: {duration:.2f}s ({duration/60:.2f}min)")
    outfile.write(f"CPU in top 5% (threshold: {cpu_95_percentile:.2f}%): {len(df[df['cpu_usage'] >= cpu_95_percentile])} measurements")

# Create plots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

ax1.plot(df['time'], df['memory_used'], marker='o', linewidth=2, markersize=4)
ax1.axhline(y=avg_memory, color='r', linestyle='--', label=f'Average: {avg_memory:.2f} MiB')
ax1.set_ylabel('Memory (MiB)')
ax1.set_title('Memory usage over time')
ax1.legend()
ax1.grid(True)

ax2.plot(df['time'], df['cpu_usage'], marker='o', linewidth=2, markersize=4, color='orange')
ax2.axhline(y=cpu_95_percentile, color='r', linestyle='--', label=f'95 percentile: {cpu_95_percentile:.2f}%')
ax2.set_xlabel('Time (seconds)')
ax2.set_ylabel('CPU (%)')
ax2.set_title('CPU usage over time')
ax2.legend()
ax2.grid(True)

plt.tight_layout()
plt.savefig('memory_cpu_usage_{}.png'.format(input_file))
plt.show()