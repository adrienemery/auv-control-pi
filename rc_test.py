"""
Utility script to print rc input from all channels to console
"""


from navio.rcinput import RCInput
import time

rc = RCInput()

while True:
    output = ''
    for channel in range(14):
        output += '{}: {}, '.format(channel, rc.read(channel))

    print(output)
    time.sleep(0.1)

