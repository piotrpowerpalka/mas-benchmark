import spade
import sys
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.behaviour import OneShotBehaviour
import time
from informAgent import *
from queryAgent import *
from initAgent import *
import traceback
import argparse

parser = argparse.ArgumentParser(description="Multi-agent benchmark")
parser.add_argument("-s", "--server", type=str, help="Server hostname", default="serverhello")
parser.add_argument("-p", "--password", type=str, help="Agent password", default="123456789")
parser.add_argument("-n", "--numagents", type=int, help="Total number of agents", default=10)
parser.add_argument("-f", "--fromag", type=int, help="Starting agent number on this docker", default=0)
parser.add_argument("-t", "--toag", type=int, help="Ending agent number on this docker", default=9)
parser.add_argument("-c", "--communication-type", type=str, help="Type of communication [inform|query|cfp|negotiation]", default="inform")
parser.add_argument("-x", "--content-size", type=int, help="Size of content [bytes]", default="1024")
parser.add_argument("-r", "--repetitions-num", type=int, help="Number of repetitions", default="10")
parser.add_argument("-i", "--initag", type=int, help="Initialize the initAwgent", default=0)
args = parser.parse_args()


async def main():
    agarr = []

    config = {}
    config["numagents"] = args.numagents
    config["server"] = args.server
    config["password"] = args.password
    config["fromag"] = args.fromag
    config["toag"] = args.toag
    config["initag"] = args.initag
    config["communication-type"] = args.communication_type
    config["content-size"] = args.content_size
    config["repetitions-num"] = args.repetitions_num

    for cnt in range(config["fromag"], config["toag"] + 1):
        aname = "agent{}@{}".format(cnt, config["server"])
        print(f"Initalizing agent {aname}")
        
        if config["communication-type"] == "inform":
            agnt = informAgent(aname, config["password"], verify_security=False)
            agnt.set("server", config["server"])
            agnt.set("fromag", config["fromag"])
            agnt.set("toag", config["toag"])
            agnt.set("numagents", config["numagents"])
            agnt.set("content-size", config["content-size"])
            agnt.set("repetitions-num", config["repetitions-num"])

            agarr.append(agnt)

        if config["communication-type"] == "query":
            agnt = queryAgent(aname, config["password"], verify_security=False)
            agnt.set("server", config["server"])
            agnt.set("fromag", config["fromag"])
            agnt.set("toag", config["toag"])
            agnt.set("numagents", config["numagents"])
            agnt.set("content-size", config["content-size"])
            agnt.set("repetitions-num", config["repetitions-num"])

            agarr.append(agnt)

    if config["initag"] == 1:
        initag = initAgent("agent-init@{}".format(config["server"]), config["password"], verify_security=False)
        initag.set("server", config["server"])
        initag.set("fromag", config["fromag"])
        initag.set("toag", config["toag"])
        initag.set("numagents", config["numagents"])


    try:
        for ag in agarr:
            print(f"Running agent {ag.name}")
            await ag.start(auto_register=True)

        if config["initag"] == 1:
            print("Running init agent")        
            await initag.start(auto_register=True)
            
    except Exception as exception:
        print(traceback.format_exc()) # This line is for getting traceback.
        print(sys.exc_info()[2]) # This line is getting for the error type.            break

    while True:
        try:
            await asyncio.sleep(60)
        except:
            print(traceback.format_exc()) # This line is for getting traceback.
            print(sys.exc_info()[2]) # This line is getting for the error type.            break
            break

if __name__ == "__main__":
    print("Starting...")
    spade.run(main())
