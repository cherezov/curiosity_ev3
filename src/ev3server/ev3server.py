# @file ev3server.py
# @author Pavel Cherezov (cherezov.pavel@gmail.com)

import time
import socket
import select
from subprocess import call

__version__ = '0.7'

class ev3devEmulator:
   def __init__(self):
      print('ev3 emulator started.')

   class LargeMotor:
      def __init__(self, name):
         print('Large motor "{}" created.'.format(name) )

   class Sound:
      def __init__(self):
         pass

      def speak(self, text):
         return self

      def wait(self):
         pass

try:
   import ev3dev.ev3 as ev3
except:
   print('Error: ev3dev module not found!')
   ev3 = ev3devEmulator()

class EV3Server:
   def __init__(self, port, quite):
      self.host = socket.gethostbyname(socket.getfqdn())
      self.port = port
      self.quite = quite
      self.__socket = None
      self.__started = False
      self.__peer_sock = None
      self.__peer_addr = None

      self.__leftMotor = ev3.LargeMotor('outB')
      self.__rightMotor = ev3.LargeMotor('outC')

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

         
         for i in range(10):
            ev3.Leds.set_color(ev3.Leds.LEFT, ev3.Leds.RED)
            ev3.Leds.set_color(ev3.Leds.RIGHT, ev3.Leds.RED)
            time.sleep(0.5)
            ev3.Leds.set_color(ev3.Leds.LEFT, ev3.Leds.GREEN)
            ev3.Leds.set_color(ev3.Leds.RIGHT, ev3.Leds.GREEN)
            time.sleep(0.2)
      except Exception as e:
         self.__log('* failed to start: {}'.format(e))

   def reply(self):
      pass

   def handle(self, cmd, value):
      if cmd == 'speak':
         self.__log('* Speaking "{}"'.format(value))
         ev3.Sound.speak(value).wait()
      elif cmd == 'test':
         self.__log('* test "{}"'.format(value))
      elif cmd == 'led':
         if value == 'green':
            ev3.Leds.set_color(ev3.Leds.LEFT, ev3.Leds.GREEN)
            ev3.Leds.set_color(ev3.Leds.RIGHT, ev3.Leds.GREEN)
         elif value == 'red':
            ev3.Leds.set_color(ev3.Leds.LEFT, ev3.Leds.RED)
            ev3.Leds.set_color(ev3.Leds.RIGHT, ev3.Leds.RED)
         elif value == 'orange':
            ev3.Leds.set_color(ev3.Leds.LEFT, ev3.Leds.ORANGE)
            ev3.Leds.set_color(ev3.Leds.RIGHT, ev3.Leds.ORANGE)
         elif value == 'yellow':
            ev3.Leds.set_color(ev3.Leds.LEFT, ev3.Leds.YELLOW)
            ev3.Leds.set_color(ev3.Leds.RIGHT, ev3.Leds.YELLOW)
      elif cmd == 'restart':
         self.__log('* restarting..')

         ev3.Leds.set_color(ev3.Leds.LEFT, ev3.Leds.YELLOW)
         ev3.Leds.set_color(ev3.Leds.RIGHT, ev3.Leds.YELLOW)

         call(['python3.4', '/usr/local/bin/ev3server.daemon.py', 'restart'])
      elif cmd == 'update':
         self.__log('* updating..')

         ev3.Leds.set_color(ev3.Leds.LEFT, ev3.Leds.GREEN)
         ev3.Leds.set_color(ev3.Leds.RIGHT, ev3.Leds.GREEN)

         ev3.Leds.set_color(ev3.Leds.LEFT, ev3.Leds.ORANGE)
         ev3.Leds.set_color(ev3.Leds.RIGHT, ev3.Leds.ORANGE)

         call(['scp', 'root@wrt:ev3server.update/ev3server.daemon.py', '/usr/local/bin'])
         call(['scp', 'root@wrt:ev3server.update/ev3server.py', '/usr/local/bin'])
         call(['scp', 'root@wrt:ev3server.update/daemon.py', '/usr/local/bin'])
         call(['scp', 'root@wrt:ev3server.update/ev3server.cfg', '/usr/local/etc'])

         ev3.Leds.set_color(ev3.Leds.LEFT, ev3.Leds.GREEN)
         ev3.Leds.set_color(ev3.Leds.RIGHT, ev3.Leds.GREEN)
      elif cmd == 'xy':
         x, y = value.split(';')
         x = float(x)
         y = float(y)
         self.__leftMotor.speed_sp = self.__leftMotor.max_speed / 10 * x
         self.__leftMotor.run_forever()
         self.__rightMotor.speed_sp = self.__rightMotor.max_speed / 10 * y
         self.__rightMotor.run_forever()
      elif cmd == 'motorA':
         self.__log('* motorA={}'.format(value))
      elif cmd == 'motorB':
         self.__log('* motorB={}'.format(value))
      elif cmd == 'smallMotor':
         self.__log('* smallMotor={}'.format(value))
      else:
         self.__log('Unknown command "{0}"'.format(cmd))

   def accept(self):
      while self.__started:
         self.__log('* waiting for peer...')
         self.__peer_sock, self.__peer_addr = self.__socket.accept()
         self.__log('* peer connected {}'.format(self.__peer_addr))
         while self.__started:
            r, w, x = select.select([self.__peer_sock], [self.__peer_sock], [], 1)
            if self.__peer_sock in r:
               datas = self.__peer_sock.recv(128).decode().strip()
               if not datas:
                  self.__log('* Connection closed')
                  break;

               for data in datas.split('|'):
                  data = data.strip()
                  if data.lower() == 'quit':
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
            elif self.__peer_sock in x:
               self.__log('* Connection closed')
               break

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

def run():
   import configparser
   import os

   print('cwd = {}\n'.format(os.getcwd()))
   config = configparser.ConfigParser()
   config.read('/usr/local/etc/ev3server.cfg')

   srvCfg = config['server']
   port = int(srvCfg['port'])
   quite = srvCfg['quite'] == 'yes' or srvCfg['quite'] == 'true'

   server = EV3Server(port, quite)
   try:
      server.start()
      server.accept()
   except KeyboardInterrupt:
      pass
   except Exception:
      print('Exception')
   finally:
      server.stop()

if __name__ == '__main__':
   run()
