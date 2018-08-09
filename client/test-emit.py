import socketio
import eventlet
import eventlet.wsgi
                      
sio = socketio.Server()

sio.emit('shake',{'data': 'shaking','mac':'00:55:DA:B3:94:D9'})

if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 8120)), socketio.Middleware(sio))
