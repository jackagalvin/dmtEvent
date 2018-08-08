from liblo import *
import time
import sys
class Ui_Listener(ServerThread):
    def __init__(self):
        ServerThread.__init__(self, 6001)

    @make_method('/change_mac', 's')
    def new_muse_mac(self, path, args):
        mac = args
        print "received message '%s' with arguments: %s" % (path, mac)

try:
    server = Ui_Listener()
except ServerError, err:
    print(str(err))
    sys.exit()
server.start()

while(1):
    time.sleep(1)
