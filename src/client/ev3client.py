# @file ev3client.py
# @author Pavel Cherezov (cherezov.pavel@gmail.com)

import io
import os
import sys
import time
import pygame
import socket
import threading
import queue
import select
from urllib.request import urlopen

__version__ = '0.4'

import configparser

config = configparser.ConfigParser()
config.read('ev3client.cfg')

mr3020Cfg = config['mr3020-board']
GATE_IP = mr3020Cfg['ip']
GATE_PORT= int(mr3020Cfg['port'])

frameCfg = config['camera-frame']
CAMERA_URL_FORMAT = frameCfg['camera-url']
FRAME_PORT = int(frameCfg['port'])

FRAME_SIZE = (int(frameCfg['width']), int(frameCfg['height']))   # must be synced with web camera settings
FRAME_POS = (int(frameCfg['pos-x']), int(frameCfg['pos-y']))

windowCfg = config['window']
SCREEN_SIZE = (int(windowCfg['width']), int(windowCfg['height']))
IMG_FOLDER = windowCfg['img-path']

TXT_X = FRAME_POS[0] + FRAME_SIZE[0] + 50

settingsCfg = config['settings']
LOW_POWER = float(settingsCfg['battery-warn'])
ALIVE_SEC = float(settingsCfg['ping-warn'])
MIN_DISTANCE = float(settingsCfg['distance-warn'])

RED = pygame.Color(settingsCfg['warn-color'])
LIGHT_GREEN = pygame.Color(95, 190, 190)

class WebFrame:
   def __init__(self, ip, port):
      self.ip = ip
      self.port = port

      self.__frame = pygame.image.load(os.path.join(IMG_FOLDER, 'noise.jpg'))
      self.__frame = pygame.transform.scale(self.__frame, FRAME_SIZE)

      self.started = True
      self.__thread = threading.Thread(target=self.frameLoop)
      self.__thread.daemon = True
      self.__thread.start()

   def __getFrame(self):
      try:
         frame_url = CAMERA_URL_FORMAT.format(self.ip, self.port)
         image_str = urlopen(frame_url).read()
         image_file = io.BytesIO(image_str)
         frame = pygame.image.load(image_file)
      except:
         # Show noise in case of errors
         frame = pygame.image.load(os.path.join(IMG_FOLDER, 'noise.jpg'))
         frame = pygame.transform.scale(frame, FRAME_SIZE)
      return frame

   def frameLoop(self):
      while self.started:
         self.__frame = self.__getFrame()

   def getFrame(self):
      return self.__frame

   def stop(self):
      self.started = False
      #self.__thread.join()

class Cmd:
   KeyValDelimiter = ':'

   def __init__(self, cmd, value):
      self.cmd = cmd
      self.value = value

   @staticmethod
   def parse(raw):
      if Cmd.KeyValDelimiter not in raw:
         return Cmd(None, None)
      return Cmd(*raw.split(Cmd.KeyValDelimiter)[:2])

   def __repr__(self):
      return '{}{}{}'.format(self.cmd, Cmd.KeyValDelimiter, self.value)

class CmdTransport:
   def __init__(self, ip, port):
      self.ip = ip
      self.port = port
      self.__queue = queue.Queue()
      self.in_queue = queue.Queue()
      self.__socket = None
      self.__prevCmd = None

      self.started = True
      self.__thread = threading.Thread(target=self.__processLoop)
      self.__thread.daemon = True
      self.__thread.start()

   def isReady(self):
      return self.__socket is not None

   def send(self, cmd):
      cmd = str(cmd)
      if cmd == self.__prevCmd:
         return
      self.__queue.put_nowait(cmd)
      self.__prevCmd = cmd

   def __processLoop(self):
      self.__socket = self.__connect()
      if self.__socket is None:
         return
      while self.started:
         try:
            r, w, x = select.select([self.__socket], [self.__socket], [], 1)
            if self.__socket in r:
               data = self.__socket.recv(128).decode()
               self.in_queue.put(data)
            if self.__socket in w:
               cmd = self.__queue.get_nowait()
               self.__socket.sendall(cmd.encode())
         except Exception as e:
            print(e)
            pass

   def __connect(self):
      try:
         print('Connecting to {}:{}', self.ip, self.port)
         s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
         s.connect((self.ip, self.port))
         print('Connected')
         return s
      except Exception as e:
         print(e)
         return None

   def stop(self):
      self.started = False
      #self.__thread.join()

class Joystick:
   def __init__(self):
      self.__joystick = None
      self.__prev_x = 0
      self.__prev_y = 0
      self.__initJoiystick()

   def __initJoiystick(self):
      pygame.joystick.init()
      if pygame.joystick.get_count() == 0:
         return

      joystickId = 0
      self.__joystick = pygame.joystick.Joystick(joystickId)
      self.__joystick.init()

   def isReady(self):
      return self.__joystick is not None

   def read(self):
      data = []
      if self.__joystick is None:
         return data

      axes = self.__joystick.get_numaxes()
      x = self.__joystick.get_axis(0)
      y = self.__joystick.get_axis(1)
      x = int(x * 100) / 10
      y = int(y * 100) / 10
      if abs(x) < 2:
         x = 0
      if abs(y) < 2:
         y = 0
      if self.__prev_x != x or self.__prev_y != y:
         data.append(Cmd('xy', '{};{}'.format(x, y)))
         self.__prev_x = x
         self.__prev_y = y

      buttons = self.__joystick.get_numbuttons()
      for i in range( buttons ):
         if i == 0:
            button = self.__joystick.get_button( i )
            if button == 1:
               with open('say') as f:
                  l = f.readline()
                  data.append(Cmd('speak', l))
         if i == 1:
            button = self.__joystick.get_button( i )
            if button == 1:
               data.append(Cmd('get', 'in'))
            elif button == 0:
               data.append(Cmd('get', 'out'))
      return data

def sumd(e1, e2):
   return [e1[i] + e2[i] for i in range(len(e1))]

class RoboControl:
   def __init__(self):
      pygame.init()
      self.__webFrame = None
      self.__cmdTransport = None
      self.__joystick = None
      self.__screen = None
      self.__clock = pygame.time.Clock()
      self.__font = pygame.font.SysFont('Arial', 25)
      self.__last_ir_value= 0
      self.__last_ping_time = 0
      self.__last_power_value = 0

      self.__move_ticker = 0
      self.__move_power = 0

   def run(self, joystick = Joystick):
      self.__initScreen()
      self.__joystick = joystick()
      self.__webFrame = WebFrame(GATE_IP, FRAME_PORT)
      self.__cmdTransport = CmdTransport(GATE_IP, GATE_PORT)
      self.__loop()

   def __txtRow(self, render, row):
      hrow = 50
      self.__screen.blit(render, (TXT_X, FRAME_POS[1] + hrow * (row - 1)))

   def __initScreen(self):
      self.__screen = pygame.display.set_mode(SCREEN_SIZE)
      pygame.display.set_caption('Legowrt v.{}'.format(__version__))

      ico = pygame.image.load(os.path.join(IMG_FOLDER, 'icon.jpg'))
      pygame.display.set_icon(ico)

      self.__bkgnd_img = pygame.image.load(os.path.join(IMG_FOLDER, 'frame.jpg'))

   def __dispatchResponse(self):
      while not self.__cmdTransport.in_queue.empty():
         data = self.__cmdTransport.in_queue.get_nowait()
         cmd = Cmd.parse(data)
         if cmd.cmd == 'ir':
            self.onIR(cmd)
         elif cmd.cmd == 'ping':
            self.onPing(cmd)
         elif cmd.cmd == 'power':
            self.onPower(cmd)

   def onPing(self, cmd):
      self.__last_ping_time = time.time()

   def onIR(self, cmd):
      self.__last_ir_value = cmd.value

   def onPower(self, cmd):
      self.__last_power_value = cmd.value

   def __handlePing(self):
      alive = time.time() - self.__last_ping_time < ALIVE_SEC
      txt = 'LEGO connection lost'
      color = RED
      if alive:
         txt = 'Connected'
         color = LIGHT_GREEN
      else:
         self.__last_ir_value = '0'

      render = self.__font.render(txt, True, color)
      self.__txtRow(render, row=1)

   def __handlePower(self):
      try:
         val = float(self.__last_power_value)
      except:
         return
      ok = val > LOW_POWER
      txt = 'Low brick battery {}V'.format(val)
      color = RED
      if ok:
         txt = 'Battery {}V'.format(val)
         color = LIGHT_GREEN

      render = self.__font.render(txt, True, color)
      self.__txtRow(render, row=2)

   def __joysticStatus(self):
      ok = self.__joystick.isReady()
      txt = 'Joystick disconnected'
      color = RED
      if ok:
         txt = 'Joystick ready'
         color = LIGHT_GREEN

      render = self.__font.render(txt, True, color)
      self.__txtRow(render, row=3)

   def __handleDistance(self):
      try:
         val = int(self.__last_ir_value)
      except:
         return
      color = LIGHT_GREEN if val > MIN_DISTANCE else RED
      dist = int(val / 10) * '='
      render = self.__font.render('{} {}>|'.format(val, dist), True, color)
      self.__txtRow(render, row=10)

   def __loop(self):
      while True:
         self.__screen.blit(self.__bkgnd_img, (0, 0))

         frame = self.__webFrame.getFrame()
         self.__screen.blit(frame, FRAME_POS)

         self.__dispatchResponse()
         self.__handleDistance()
         self.__handlePing()
         self.__handlePower()
         self.__joysticStatus()

         keys=pygame.key.get_pressed()
         if keys[pygame.K_ESCAPE]:
            return
         if keys[pygame.K_LEFT]:
            if self.__move_ticker == 0:
               self.__move_ticker = 2 
            print('Left pwr={}'.format(self.__move_power))
         if keys[pygame.K_RIGHT]:
            if self.__move_ticker == 0:   
               self.__move_ticker = 2     
            print('Right pwr={}'.format(self.__move_power))
         if keys[pygame.K_UP]:
            if self.__move_ticker == 0:
               self.__move_ticker = 2
            print('Up pwr={}'.format(self.__move_power))
         if keys[pygame.K_DOWN]:
            if self.__move_ticker == 0:   
               self.__move_ticker = 2    
            print('Down pwr={}'.format(self.__move_power))

         if self.__move_ticker > 0:
             self.__move_ticker -= 1


         pygame.display.flip()

         data = self.__joystick.read()
         for cmd in data:
            self.__cmdTransport.send(cmd)

         for event in pygame.event.get():
            if event.type == pygame.QUIT:
               self.__webFrame.stop()
               self.__cmdTransport.stop()
               sys.exit()
         self.__clock.tick(60)

if __name__ == '__main__':
   import sys
   c = RoboControl()

   class JoystickTest:
      def __init__(self):
         pass

      def isReady(self):
         return True

      def read(self):
         return [Cmd('test', 'test')]

   c.run(JoystickTest)
