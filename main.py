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


DEFAULT_HOST = "serverhello"
AGENT_PASSWORD = "123456789"


async def main():
    print("Starting...")
    agarr = []

    for cnt in range(0,10):
        aname = "agent{}@{}".format(cnt, DEFAULT_HOST)
        print(f"Initalizing agent {aname}")
        agnt = testAgent(aname, AGENT_PASSWORD, verify_security=False)
        agarr.append(agnt)    
    
    initag = initAgent("initagent@{}".format(DEFAULT_HOST), AGENT_PASSWORD, verify_security=False)

    try:
        for cnt in range(0,10):
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
