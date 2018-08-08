from muse import Muse
from liblo import *
import time
import requests


address = "00:55:DA:B3:94:D9"
host = "192.168.0.146"
port = 1337
backend = 'gatt'
device_type = "muse"
current_muse = None
ui_server = None


class Ui_Listener(ServerThread):
    def __init__(self):
        ServerThread.__init__(self, 6001)

    @make_method('/change_mac', 's')
    def new_muse_mac(self, path, args):
        global current_muse
        print("message recieved")
        current_muse.disconnect()
        if(args!='disconnected'):
            current_muse = connect_muse(args,device_type,host,port,callback,backend)
            print("connected to %s" % (args))
        else:
            print("disconnecting muse")


countACC=0
def process():
    global now
    global countACC
    now = time.time()
    countACC+=1.0

def start_ui_server():
    server = Ui_Listener()
    print('ui_listener created')
    server.start()
    print('ui_listener started')
    requests.post("http://192.168.0.146:8000/api/connect-pi", data={'mac':'B8:27:EB:74:F9:40','status':address})


def connect_muse(address,device_type,host,port,callback):
    muse = Muse(address=address,device_type=device_type,host=host,port=port,callback=process,backend=backend,interface=None)
    muse.connect()
    print("muse connected %s" %(address))
    muse.start()
    print("muse streaming from %s" % (address))
    return muse

def initialise(address,device_type,host,port,backend):
    global current_muse
    current_muse = connect_muse(address,device_type,host,port,backend)
    start_ui_server()

def main():
    initialise(address,device_type,host,port,backend)
    run()
'''
def run():
    global current_muse
    idx =0
    losshist =[0 for i in range(10)]
    global countACC
    while 1:
        try:
            time.sleep(1)
            dataloss =max(0.0,100.0-countACC*3/50*100.0)
            losshist[idx] = dataloss
            idx=(idx+1)%10
            avgloss =sum(losshist)/float(len(losshist))
            if current_muse != None:
                print(current_muse.address)
            else:
                print("None")
            countACC = 0
            if ((time.time()-now)>500):
                break
            if ((avgloss>40)):
                break
        except:
            print("failed")
            break


    current_muse.disconnect()
'''
def run():
    while 1:
        time.sleep(1)

main()

