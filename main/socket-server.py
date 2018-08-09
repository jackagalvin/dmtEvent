import socketio
import eventlet
import eventlet.wsgi
from threading import Lock


thread = None
thread_lock = Lock()

def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(1)
        print("sendong message")
        count += 1
        socketio.emit('my_response',
                      {'data': 'Server generated event', 'count': count},
                      namespace='/status')
                      
                      
sio = socketio.Server()

@sio.on('connect', namespace='/status')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})

@sio.on('shake', namespace='/status')
def shake(sid, environ):
    print("shaking", sid)
    sio.emit('shaking')

@sio.on('my_event', namespace='/connect')
def test_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})

if __name__ == '__main__':
    app = socketio.Middleware(sio)
    eventlet.wsgi.server(eventlet.listen(('', 8100)), app)
