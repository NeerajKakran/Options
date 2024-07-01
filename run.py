import os
from time import sleep

for i in range(87):
    os.subprocess.run('python option_live_trigger.py')
    sleep(60*5)
