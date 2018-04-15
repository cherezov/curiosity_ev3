#!/usr/bin/python3.4
# @file ev3server.py
# @author Pavel Cherezov (cherezov.pavel@gmail.com)

import time
import socket
import select
import threading
import queue
from subprocess import call

__version__ = '0.8'

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

      self.__leftMotor = ev3.LargeMotor('outD')
      self.__rightMotor = ev3.LargeMotor('outA')
      self.__smallMotor = ev3.MediumMotor('outC')
      self.__ir = ev3.InfraredSensor()
      self.__power = ev3.PowerSupply()

      self.__last_ping = 0
      self.__last_ir = 0
      self.__last_pwr = 0

      self.__gear = 1


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
      try:
         if time.time() - self.__last_ping > 1.5: 
            self.__peer_sock.sendall('ping:ok;'.encode()) 
            self.__last_ping = time.time() 
    
         if time.time() - self.__last_pwr > 2: 
            self.__peer_sock.sendall('power:{};'.format(self.__power.measured_volts).encode()) 
            self.__last_pwr = time.time() 

         if time.time() - self.__last_ir > 1: 
            self.__peer_sock.sendall('ir:{};'.format(self.__ir.value()).encode()) 
            self.__last_ir = time.time() 
      except:
         pass
 
   def handle(self, cmd, value):
      if cmd == 'speak':
         self.__log('* Speaking "{}"'.format(value))
         ev3.Sound.speak(value).wait()
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
      elif cmd == 'shutdown':
         self.__log('* shutting down..')

         ev3.Leds.set_color(ev3.Leds.LEFT, ev3.Leds.RED)
         ev3.Leds.set_color(ev3.Leds.RIGHT, ev3.Leds.RED)

         call(['shutdown', '-h', 'now'])
      elif cmd == 'xy':
         x, y = value.split(',')
         x = float(x)
         y = float(y)
         self.__leftMotor.speed_sp = self.__leftMotor.max_speed / self.__gear * x
         self.__leftMotor.run_forever()
         self.__rightMotor.speed_sp = self.__rightMotor.max_speed / self.__gear * y
         self.__rightMotor.run_forever()
      elif cmd == 'arm':
         value = float(value)
         direction = 1 if value > 0 else -1
         self.__log('* arm {}..'.format('open' if direction == 1 else 'close'))
         self.__smallMotor.run_timed(time_sp=abs(value), speed_sp=direction * 360)
      elif cmd == 'gear':
         self.__gear = int(value)
      elif cmd == 'arm_open':
         self.__log('* arm open..')
         self.__smallMotor.run_timed(time_sp=1000, speed_sp=360)
      elif cmd == 'arm_close':
         self.__log('* arm close..')
         self.__smallMotor.run_timed(time_sp=1000, speed_sp=-360)
      elif cmd == 'drive':
         left, right = value.split(',')
         left = -float(left)
         right = -float(right)
         self.__leftMotor.speed_sp = self.__leftMotor.max_speed / self.__gear * left
         self.__leftMotor.run_forever()
         self.__rightMotor.speed_sp = self.__rightMotor.max_speed / self.__gear * right
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
         self.__peer_sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
         self.__log('* peer connected {}'.format(self.__peer_addr))
         while self.__started:
            self.reply()

            r, w, x = select.select([self.__peer_sock], [self.__peer_sock], [], 1)
            if self.__peer_sock in r:
               datas = self.__peer_sock.recv(128).decode().strip()
               if not datas:
                  self.__log('* Connection closed')
                  break

               for data in datas.split(';'):
                  data = data.strip()
                  if data.lower() == 'quit':
                     self.__log('* peer is going to disconnect')
                     self.__peer_sock.close()
                     self.__log('* peer disconnected')
                     break
                  self.__log('* Received: "{}"'.format(data))

                  if ':' in data:
                     try:
                        cmd, value = data.split(':')
                        self.handle(cmd.strip(), value.strip())
                     except Exception as e:
                        print('Handle exception: {}'.format(e))

            if self.__peer_sock in x:
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
   except Exception as e:
      print('Exception:', e)
   finally:
      server.stop()

if __name__ == '__main__':
   run()
