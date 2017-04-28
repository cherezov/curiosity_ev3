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

__version__ = '0.3'

GATE_IP = "192.168.1.120" # ip address of MR3020 board
GATE_PORT= 88             # port number on MR3020 board which redirects to lego
FRAME_PORT = 8080         # webcamera port on MR3020
FRAME_SIZE = (640, 480)   # must be synced with web camera settings
SCREEN_SIZE = (1000, 650)
FRAME_POS = (25, 80)
IMG_FOLDER = '../../images/'
CAMERA_URL_FORMAT = 'http://{}:{}/?action=snapshot'

class WebFrame:
   def __init__(self, ip, port):
      self.ip = ip
      self.port = port

      self.__frame = pygame.image.load(os.path.join(IMG_FOLDER, 'noise.jpg'))
      self.__frame = pygame.transform.scale(self.__frame, FRAME_SIZE)

      self.started = True
      self.__thread = threading.Thread(target=self.frameLoop, daemon=True)
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
   def __init__(self, cmd, value):
      self.cmd = cmd
      self.value = value

   def __repr__(self):
      return '{}:{}|'.format(self.cmd, self.value)

class CmdSender:
   def __init__(self, ip, port):
      self.ip = ip
      self.port = port
      self.__queue = queue.Queue()
      self.in_queue = queue.Queue()
      self.__socket = None
      self.__prevCmd = None

      self.started = True
      self.__thread = threading.Thread(target=self.__processLoop, daemon=True)
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
               pass
         except Exception as e:
            pass

   def __connect(self):
      try:
         s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
         s.connect((self.ip, self.port))
         return s
      except:
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

   def get(self):
      data = []
      if self.__joystick is None:
         return data

      # TODO: think about this calculations
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
               data.append(Cmd('speak', 'Hello. I am robot.'))
      return data

class RoboControl:
   def __init__(self):
      pygame.init()
      self.__webFrame = None
      self.__cmdSender = None
      self.__joystick = None
      self.__screen = None
      self.__clock = pygame.time.Clock()
      self.__font = pygame.font.SysFont('Arial', 25)
      self.__ir_val = 0
      self.__last_ping_time = 0

   def loop(self):
      self.__initScreen()
      self.__joystick = Joystick()
      self.__webFrame = WebFrame(GATE_IP, FRAME_PORT)
      self.__cmdSender = CmdSender(GATE_IP, GATE_PORT)

      # Checkers
      #self.__button('green' if self.__cmdSender.isReady else 'red', (730, 200), (200, 50), 'Lego connection', 'blue', (760, 210))

      self.__loop()

   def __button(self, bcolor, xy, wh, text, tcolor, txy):
      btnColor = pygame.Color(bcolor)
      txtColor = pygame.Color(tcolor)
      pygame.draw.rect(self.__screen, btnColor, (xy[0], xy[1], wh[0], wh[1]))
      self.__screen.blit(self.__font.render(text, True, txtColor), txy)
      pygame.display.update()

   def __initScreen(self):
      self.__screen = pygame.display.set_mode(SCREEN_SIZE)
      pygame.display.set_caption('Robot controller v.{}'.format(__version__))

      ico = pygame.image.load(os.path.join(IMG_FOLDER, 'icon.jpg'))
      pygame.display.set_icon(ico)

      bkgnd = pygame.image.load(os.path.join(IMG_FOLDER, 'tunnel.jpg'))
      self.__screen.blit(bkgnd, (0, 0))

      pygame.draw.rect(self.__screen, pygame.Color('orange'), (FRAME_POS[0] - 5, FRAME_POS[1] - 5, FRAME_SIZE[0] + 10, FRAME_SIZE[1] + 10))
      pygame.display.update()

   def __loop(self):
      while True:
         frame = self.__webFrame.getFrame()
         self.__screen.blit(frame, FRAME_POS)

         while not self.__cmdSender.in_queue.empty():
            data = self.__cmdSender.in_queue.get_nowait()
            if data.startswith('ir'):
               self.__ir_val = data.split(':')[1]
            elif data.startswith('ping'):
               self.__last_ping_time = time.time()

         dead = time.time() - self.__last_ping_time > 5
         if dead:
            self.__button('red', (730, 120), (200, 50), 'Brick lost', 'blue', (790, 130))
            self.__ir_val = 'ERROR'
         else:
            self.__button('green', (730, 120), (200, 50), 'Brick ready', 'blue', (790, 130))

         self.__screen.blit(self.__font.render('distance: {}cm'.format(self.__ir_val), True, pygame.Color('red')), (FRAME_POS[0] + FRAME_SIZE[0] - 300, FRAME_POS[1]+FRAME_SIZE[1]-50))
         pygame.display.flip()

         data = self.__joystick.get()
         for cmd in data:
            self.__cmdSender.send(cmd)

         for event in pygame.event.get():
            if event.type == pygame.QUIT:
               self.__webFrame.stop()
               self.__cmdSender.stop()
               sys.exit()
         self.__clock.tick(60)

if __name__ == '__main__':
   c = RoboControl()
   c.loop()
