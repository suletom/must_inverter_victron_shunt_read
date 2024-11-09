#run from crontab: @reboot root screen -d -m -S kijelzo && sleep 2 && screen -S kijelzo -p 0 -X stuff 'python3 /home/pi/Desktop/inverter_kijelzo/script.py^M'
from sense_hat import SenseHat
import os
import time
import re
from datetime import datetime
import threading


modbus_command="modbus /dev/ttyUSB0 -s 4 -b 19200 -t 10 -p 1 -P n"

def get_modbus(comm,sdef):
    stream = os.popen(modbus_command+" "+sdef)
    output = stream.read()
    tmp = output.splitlines()
    if len(tmp) > 1:
        tmps=tmp[1]
        data = tmps.split(' ')
        if len(data) > 1:
            return data[1]
    return ""


def get_victron():
    stream = os.popen("timeout 2 gatttool -b CB:B2:A1:CB:77:A9 -t random --char-read --uuid 65970fff-4bda-4c1e-af4b-551c4cf74769")
    output = stream.read()
    #print(output)
    tmp = output.splitlines()
    if len(tmp) >= 1:
        #print("line: "+tmp[0])
        rt = re.search("value: ([0-9a-f]{2}) ([0-9a-f]{2})",tmp[0])
        if rt is not None:
            it = "0x"+rt.group(2)+rt.group(1)
            #print(it)
            ival=int(it, base=16)
            return ival
    return -1

def lineind(sense,line,percent):

    g = (0, 255, 0)
    r = (255, 0, 0)
    o = (255, 165, 0)
    b = (0, 0, 0)

    for i in range(0, 8):
        color = b
        if i == 0 and percent > 0:
            color = g
        if i == 1 and percent > ((100/8)*1):
            color = g
        if i == 2 and percent > ((100/8)*2):
            color = g
        if i == 3 and percent > ((100/8)*3):
            color = g
        if i == 4 and percent > ((100/8)*4):
            color = g
        if i == 5 and percent > ((100/8)*5):
            color = g
        if i == 6 and percent > ((100/8)*6):
            color = o
        if i == 7 and percent > ((100/8)*7):
            color = r

        sense.set_pixel(i, line, color)

def line(sense,line,color):

    for i in range(0, 8):
        sense.set_pixel(i, line, color)


def lineindpn(sense,line,current,chargemax,drainmax):

    g = (0, 255, 0)
    r = (255, 0, 0)
    o = (255, 165, 0)
    b = (0, 0, 0)

    for i in range(0, 8):
        color = b
        if current < 0:
            if abs(current)/(chargemax/8) > i:
                color=o;
        if current > 0:
            if abs(current)/(drainmax/8) > i:
                color=g;

        sense.set_pixel(i, line, color)

def batind(sense,soc):

    g = (0, 255, 0)
    r = (255, 0, 0)
    o = (255, 165, 0)
    b = (0, 0, 0)

    if soc < 20:
        g = r

    for i in range(0, 8):

        for j in range(0, 4):
            color = b
            if soc/(100/8) > i:
                color = g
                if soc < 40:
                    color = o
                if soc < 20:
                    color = r

            if j == 0:
                color = g

            if j == 3:
                color = g

            if i == 0:
                color = g

            if i == 7:
                color = g

            if i == 7 and j == 0:
                color = b

            if i == 7 and j == 3:
                color = b

            sense.set_pixel(i, j, color)

def invproc():
    global loadpercent_i,batterycurrent_i,invtime

    ok=1
    #LoadPercent
    loadpercent=get_modbus(modbus_command,"h@25216/h");
    if not loadpercent.isnumeric():
        print("Loadpercent not available.")
        ok=0
    else:
       loadpercent_i=int(loadpercent)
       #print("Load %: "+loadpercent)

    #BattCurrent
    batterycurrent=get_modbus(modbus_command,"h@25274/h");
    if not batterycurrent.lstrip("-").isnumeric():
        print("BatteryCurrent not available.")
        ok=0
    else:
        batterycurrent_i=int(batterycurrent)
        #print("BatteryCurrent: "+batterycurrent)

    if ok == 1:
        invtime = datetime.now()

    time.sleep(1)

def invthread():
    while True:
        invproc()

def errblock(sense,fro,to):

    for i in range(fro, to):
       line(sense,i,(255, 0, 0))
    time.sleep(0.5)
    for i in range(fro, to):
        line(sense,i,(255, 255, 255))
    time.sleep(0.5)
    for i in range(fro, to):
        line(sense,i,(255, 0, 0))
    time.sleep(0.5)

    for i in range(fro, to):
        line(sense,i,(0, 0, 0))

def initdisp(sense):

    errblock(sense,0,8)
    time.sleep(0.5)
    errblock(sense,0,8)
    time.sleep(0.5)
    errblock(sense,0,8)
    time.sleep(0.5)
    errblock(sense,0,8)

    for i in range(0,10):
        batind(sense,i*10)
        time.sleep(0.3)

    for i in range(0,10):
        lineind(sense,7,i*10)
        time.sleep(0.2)

    for i in range(0,10):
        lineindpn(sense,5,i,10,10);
        time.sleep(0.2)

    errblock(sense,0,8)


print("Init pi sense hat...")
sense = SenseHat()
sense.low_light = True

initdisp(sense)

osoc = 0
socdate = datetime(1971, 1, 1, 0, 0, 0)
invtime = datetime(1971, 1, 1, 0, 0, 0)

loadpercent_i = 0
batterycurrent_i = 0

print("Starting battery thread...")
th1 = threading.Thread(target=invthread)
th1.start()

print("Starting main loop...")
while True:

    #gatttool -b CB:B2:A1:CB:77:A9 -t random --char-read --uuid 65970fff-4bda-4c1e-af4b-551c4cf74769
    soc = get_victron()

    if soc > -1:
        osoc=soc
        print("BatterySoc query ok")
        socdate = datetime.now()
    else:
        print("BatterySoc query fail")

    print("BatterySoc %:"+str(osoc/100))
    print("BatterySoc last query: ",socdate)
    print("-------------------------------------")
    print("BatteryCurrent: "+str(batterycurrent_i))
    print("Load: "+str(loadpercent_i))
    print("Inverter last query: ",invtime)
    lineind(sense,7,loadpercent_i)
    lineindpn(sense,5,batterycurrent_i,40,125);
    batind(sense,osoc)

    print(" ")

    difference = (invtime - datetime.now()).total_seconds()
    bdifference = (socdate - datetime.now()).total_seconds()

    if difference > 60:
        if bdifference > 300:
            errblock(sense,0,8)
        else:
            errblock(sense,5,8)
    else:
        time.sleep(1)
