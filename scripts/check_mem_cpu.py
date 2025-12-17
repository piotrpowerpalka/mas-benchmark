
import subprocess
import time
from datetime import datetime
import sys

if len(sys.argv) != 3:
    print("Usage: python check_mem_cpu.py <container_name> <output_file>")
    sys.exit(1)

CONTAINER = sys.argv[1]
OUTFILE = sys.argv[2]

while True:
  ts = datetime.now().strftime("%s.%f")[:-3]
  cmd = f'docker stats --no-stream --format "{ts};{{{{.Container}}}};{{{{.MemUsage}}}};{{{{.MemPerc}}}}" {CONTAINER}'
  result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
  
  with open(OUTFILE, "a") as f:
    f.write(result.stdout)
  
  time.sleep(0.1)