# @file ev3server.py
# @author Pavel Cherezov (cherezov.pavel@gmail.com)

import socket
import select

try:
   import ev3dev.ev3 as ev3
except:
   print('Error: ev3dev module not found!')

class EV3Server:
   def __init__(self, port, quite):
      self.host = socket.gethostbyname(socket.getfqdn())
      self.port = port
      self.quite = quite
      self.__socket = None
      self.__started = False
      self.__peer_sock = None
      self.__peer_addr = None

   def __log(self, msg):
      if not self.quite:
         print(msg)

   def start(self):
      self.__log('== EV3 Server ==')
      self.__log('* starting server {}:{}'.format(self.host, self.port))
      try:
         self.__socket = socket.socket()
         self.__socket.bind(('', self.port))
         self.__socket.listen(1)
         self.__started = True
         self.__log('* started')
      except Exception as e:
         self.__log('* failed to start: {}'.format(e))

   def reply(self):
      pass

   def handle(self, cmd, value):
      if cmd == 'speak':
         self.__log('* Speaking "{}"'.format(value))
         ev3.Sound.speak(value).wait()
      elif cmd == 'motorA':
         self.__log('* motorA={}'.format(value))
      elif cmd == 'motorB':
         self.__log('* motorB={}'.format(value))
      elif cmd == 'smallMotor':
         self.__log('* smallMotor={}'.format(value))
      else:
         self.__log('Unknown command "{0}"'.format(value))

   def accept(self):
      while self.__started:
         self.__log('* waiting for peer...')
         self.__peer_sock, self.__peer_addr = self.__socket.accept()
         self.__log('* peer connected {}'.format(self.__peer_addr))
         while self.__started:
            r, w, x = select.select([self.__peer_sock], [self.__peer_sock], [], 1)
            if self.__peer_sock in r:
               data = self.__peer_sock.recv(1024).decode()
               data = data.strip()

               if not data or data.lower() == 'quit':
                  self.__log('* peer is going to disconnect')
                  self.__peer_sock.close()
                  self.__log('* peer disconnected')
                  break
               self.__log('* Received: "{}"'.format(data))

               if ':' in data:
                  cmd, value = data.split(':')
                  try:
                     self.handle(cmd.strip(), value.strip())
                  except Exception as e:
                     print('Handle exception: {}'.format(e))
            elif self.__peer_sock in w:
               self.reply()
            
         self.__peer_sock = None
         self.__peer_addr = None

   def stop(self):
      self.__log('* stopping server')
      self.__started = False
      if self.__peer_sock is not None:
         self.__peer_sock.close()
         self.__peer_sock = None
      if self.__socket is not None:
         self.__socket.close()
         self.__socket = None

if __name__ == '__main__':
   import sys

   port = 8080
   quite = False
   for kv in sys.argv[1:]:
      key, value = kv.split('=')
      key = key.lower().strip()
      value = value.lower().strip()
      if key == 'port':
         port = int(value)
      elif key == 'quite':
         quite = value == '1' or value == 'true'
      else:
         pass

   server = EV3Server(port, quite)
   try:
      server.start()
      server.accept()
   except KeyboardInterrupt:
      pass
   finally:
      server.stop()
