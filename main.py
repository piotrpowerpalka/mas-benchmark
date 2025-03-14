import spade
import sys
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.behaviour import OneShotBehaviour
import time
import csv
import datetime
import os
import asyncio

DEFAULT_HOST = "server_hello"
AGENT_PASSWORD = "123456789"


async def main():

    repeat = True
    while(repeat == True):
        try:
            # uruchamiamy agenta Predictor dla każdego urządzenia
#            await prd_pv.start(auto_register=True)
            repeat = False
            break

        except Exception as exception:
#            print(type(exception).__name__)
            print("Nie udało się zainicjować agentów probujemy dalej....")
            time.sleep(3)
            repeat = True

#    while True:
#        try:
#            await asyncio.sleep(60)
#        except:
#            break

if __name__ == "__main__":
    spade.run(main())
