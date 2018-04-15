
import time
import socket
import select


ip = '192.168.1.120'
port = 2000

def send(s, cmd):
   print('senging:', cmd)
   s.send(cmd.encode())
   time.sleep(0.08)


print('Connecting to {}:{}'.format(ip, port))
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip, port))
#s.setblocking(0)
print('Connected')

send(s, 'gear:9;')
