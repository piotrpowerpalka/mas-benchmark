import spade
import sys
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.behaviour import OneShotBehaviour
import time
from testAgent import *
import traceback

DEFAULT_HOST = "serverhello.local"
AGENT_PASSWORD = "123456789"


async def main():
    print("Starting...")
    agarr = []

    ag0 = testAgent("agent@{}".format(DEFAULT_HOST), AGENT_PASSWORD, verify_security=False)
    await ag0.start(auto_register=True)
    print("Agent {} started".format(ag0.name))

    for cnt in range(0,10):
        aname = "agent{}@{}".format(cnt, DEFAULT_HOST)
        print(f"Initalizing agent {aname}")
        agnt = testAgent(aname, AGENT_PASSWORD, verify_security=False)
        agarr.append(agnt)    

    await agarr[0].start(auto_register=True)
    print("Agent {} started".format(agarr[0].name))

    try:
        for cnt in range(0,10):
            print(f"Running agent {agarr[cnt].name}")
            await agarr[cnt].start(auto_register=True)
            port = 10000 + cnt
            agarr[cnt].web.start(hostname="127.0.0.1", port="{}".format(port))
        
            
    except Exception as exception:
        print(traceback.format_exc()) # This line is for getting traceback.
        print(sys.exc_info()[2]) # This line is getting for the error type.            break

#    while True:
#        try:
#            await asyncio.sleep(60)
#        except:
#            break

if __name__ == "__main__":
    print("Starting...")
    spade.run(main())
