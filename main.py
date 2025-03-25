import spade
import sys
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.behaviour import OneShotBehaviour
import time
from testAgent import *
from initAgent import *
import traceback
import argparse

parser = argparse.ArgumentParser(description="Multi-agent benchmark")
parser.add_argument("-s", "--server", type=str, help="Server hostname", default="serverhello")
parser.add_argument("-p", "--password", type=str, help="Agent password", default="123456789")
parser.add_argument("-n", "--numagents", type=int, help="Total number of agents", default=10)
parser.add_argument("-f", "--fromag", type=int, help="Starting agent number on this docker", default=0)
parser.add_argument("-t", "--toag", type=int, help="Ending agent number on this docker", default=9)
args = parser.parse_args()


async def main():
    print("Starting...")
    agarr = []

    for cnt in range(args.fromag, args.toag + 1):
        aname = "agent{}@{}".format(cnt, args.server)
        print(f"Initalizing agent {aname}")
        agnt = testAgent(aname, args.password, args, verify_security=False)
        agarr.append(agnt)    
    
    initag = initAgent("initagent@{}".format(args.server), args.password, args, verify_security=False)

    try:
        for cnt in range(args.fromag, args.toag + 1):
            print(f"Running agent {agarr[cnt].name}")
            await agarr[cnt].start(auto_register=True)

        print("Running init agent")        
        await initag.start(auto_register=True)
            
    except Exception as exception:
        print(traceback.format_exc()) # This line is for getting traceback.
        print(sys.exc_info()[2]) # This line is getting for the error type.            break

    while True:
        try:
            await asyncio.sleep(60)
        except:
            break

if __name__ == "__main__":
    print("Starting...")


    spade.run(main())
