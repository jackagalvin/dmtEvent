import socketio
import eventlet
import eventlet.wsgi

import threading 

def server_worker():
                      
    sio = socketio.Server()

    @sio.on('shaking')
    def message(self,message):
        sio.emit('shake',
             {'data': 'shaking','mac':'00:55:DA:B3:94:D9'})

    if __name__ == '__main__':
        eventlet.wsgi.server(eventlet.listen(('', 8100)), socketio.Middleware(sio))

