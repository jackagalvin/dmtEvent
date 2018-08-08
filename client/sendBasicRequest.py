import requests
r = requests.post("http://192.168.1.102:8000/api/connect-pi", data={'mac':'BC-D7-B4-92-34-A2','status':'disconnected'})

