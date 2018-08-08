from muse import Muse
import time
import requests
import liblo

address = "00:55:DA:B3:94:D9"
host = "192.168.1.103"
port = 1337
backend = 'gatt'
device_type = "muse"

countACC = 0;
def process():
    global now
    global countACC
    now = time.time()
    countACC+=1.0


muse = Muse(address=address,device_type=device_type,host=host,port=port,callback=process,backend=backend,interface=None)

muse.connect()
print('Connected')
muse.start()
print('Streaming')
idx =0
losshist =[0 for i in range(10)]
while 1:
    try:
        time.sleep(1)
        dataloss =max(0.0,100.0-countACC*3/50*100.0)
        losshist[idx] = dataloss
        idx=(idx+1)%10
        avgloss =sum(losshist)/float(len(losshist))
        print('loss: %2f' % (dataloss))
        #print('waited: %2f' % (time.time()-now),  'dataloss: %.1f' % dataloss,'avgloss: %f' % avgloss )
        countACC = 0;
        if ((time.time()-now)>500):
            break
        if ((avgloss>40)):
            break
    except:
        print("failed")
        break


muse.disconnect()

