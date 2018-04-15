#!/usr/bin/python3.4
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

__version__ = '0.5'

import configparser

config = configparser.ConfigParser()
config.read('ev3client.cfg')

ARDUINO_CMD = 'arduino'
EV3_CMD = 'ev3'

mr3020Cfg = config['mr3020-board']
GATE_IP = mr3020Cfg['ip']
GATE_PORT = int(mr3020Cfg['arduino-port'])
EV3_PORT = int(mr3020Cfg['ev3-port'])

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
GREEN = pygame.Color('green')
BLACK = pygame.Color('black')
LIGHT_GREEN = pygame.Color(95, 190, 190)

def log(msg):
   if not msg.strip():
      return
   with open('log.txt', 'a') as f:
      f.write(msg)
      f.write('\n')

class WebFrame:
   def __init__(self, ip, port):

      self.ip = ip
      self.port = port

      # Show noise in case of errors
      frame = pygame.image.load(os.path.join(IMG_FOLDER, 'noise.jpg'))
      self.__noiseFrame = pygame.transform.scale(frame, FRAME_SIZE)

      frame = pygame.image.load(os.path.join(IMG_FOLDER, 'noise_black.jpg'))
      self.__noiseBlackFrame = pygame.transform.scale(frame, FRAME_SIZE)

      self.__frame = self.__noiseFrame

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
         return frame
      except:
         pass

      # Show noise in case of errors
      return self.__noiseFrame if int(time.time()) % 2 == 0 else self.__noiseBlackFrame

   def frameLoop(self):
      while self.started:
         self.__frame = self.__getFrame()
         time.sleep(0.5)

   def getFrame(self):
      return self.__frame

   def stop(self):
      self.started = False
      #self.__thread.join()

class Cmd:
   KeyValDelimiter = ':'

   def __init__(self, cmd, value, dest = None):
      self.cmd = cmd
      self.value = value
      self.dest = dest

   @staticmethod
   def parse(raw):
      if Cmd.KeyValDelimiter not in raw:
         return Cmd(None, None, None)
      return Cmd(*raw.split(Cmd.KeyValDelimiter)[:2])

   def __repr__(self):
      return '{}{}{};'.format(self.cmd, Cmd.KeyValDelimiter, self.value)

   def __eq__(self, c):
      return (self.cmd == c.cmd) and (self.value == c.value)

class CmdTransport:
   def __init__(self, ip, port, ev3port):
      self.ip = ip
      self.port = port
      self.ev3port = ev3port
      self.__queue = queue.Queue()
      self.in_queue = queue.Queue()
      self.__socket = None
      #self.__prevCmd = None

      self.__lastReconnect = None

      self.started = True
      self.__thread = threading.Thread(target=self.__processLoop)
      self.__thread.daemon = True
      self.__thread.start()

      self.__pingThread = threading.Thread(target=self.__pingThread)
      self.__pingThread.daemon = True
      self.__pingThread.start()

   def __pingThread(self):
      while self.started:
         ping = Cmd('ping', 'ping', EV3_CMD);
         self.send(ping)
         time.sleep(ALIVE_SEC - 1)

   def isReady(self):
      return self.__socket is not None

   def send(self, cmd):
      #if cmd == self.__prevCmd:
      #   return
      self.__queue.put_nowait(cmd)
      #self.__prevCmd = cmd

   def reconnectEv3(self):
      if time.time() - self.__lastReconnect > 10:
         print('reconnection..')
         self.__ev3socket = self.__connect(self.ev3port)

   def __processLoop(self):
      self.__socket = self.__connect(self.port)
      self.__ev3socket = self.__connect(self.ev3port)
      if self.__socket is None:
         return
      while self.started:
         try:
            cmd = self.__queue.get_nowait()
            cmds = str(cmd)

            if cmd.dest is None or cmd.dest == ARDUINO_CMD:
               r, w, x = select.select([self.__socket], [self.__socket], [], 1)
               if self.__socket in r:
                  data = self.__socket.recv(128).decode()
                  self.in_queue.put(data)
               if self.__socket in w:
                  print('senging to ardu:', cmds)
                  self.__socket.sendall(cmds.encode())
                  time.sleep(0.1)

            if cmd.dest is None or cmd.dest == EV3_CMD:
               r, w, x = select.select([self.__ev3socket], [self.__ev3socket], [self.__ev3socket], 1)
               if self.__ev3socket in r:
                  data = self.__ev3socket.recv(128).decode()
                  self.in_queue.put(data)
               if self.__ev3socket in w:
                  print('senging to ev3:', cmds)
                  self.__ev3socket.sendall(cmds.encode())
                  time.sleep(0.1)
         except queue.Empty:
            pass
         except Exception as e:
            print(e)

   def __connect(self, port):
      try:
         self.__lastReconnect = time.time()

         print('Connecting to {}:{}', self.ip, port)
         s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
         s.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
         s.connect((self.ip, port))
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

def text_objects(text, font):
   textSurface = font.render(text, True, BLACK)
   return textSurface, textSurface.get_rect()

class RoboControl:
   def __init__(self):
      pygame.init()
      pygame.key.set_repeat(1, 100)

      self.__webFrame = None
      self.__cmdTransport = None
      self.__joystick = None
      self.__screen = None
      self.__clock = pygame.time.Clock()
      self.__font = pygame.font.SysFont('Arial', 25)
      self.__last_ir_value= 0
      self.__last_ping_time = 0
      self.__last_power_value = 0

      frame = pygame.image.load(os.path.join(IMG_FOLDER, 'cam.png'))
      self.__camViewFrame = pygame.transform.scale(frame, (100, 100))

      self.__gear = 1

   def run(self, joystick = Joystick):
      self.__initScreen()
      #self.__joystick = joystick()
      self.__webFrame = WebFrame(GATE_IP, FRAME_PORT)
      self.__cmdTransport = CmdTransport(GATE_IP, GATE_PORT, EV3_PORT)

      self.__arm1 = 100
      cmd = Cmd('Arm1', self.__arm1)
      self.__cmdTransport.send(cmd)

      self.__arm2 = 0
      self.__cam = 0
      cmd = Cmd('Arm2', self.__arm2)
      self.__cmdTransport.send(cmd)

      self.__arm2 = 0
      self.__cam = 0
      cmd = Cmd('Arm2', self.__arm2)
      self.__cmdTransport.send(cmd)

      self.__gear = 1
      cmd = Cmd('gear', '10', EV3_CMD)
      self.__cmdTransport.send(cmd)

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
         for raw_cmd in data.split(';'):
            cmd = Cmd.parse(raw_cmd)
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
      txt = 'Brick connection lost'
      color = RED if int(time.time()) % 2 == 0 else BLACK
      if alive:
         txt = 'Brick Connected'
         color = LIGHT_GREEN
      else:
         self.__cmdTransport.reconnectEv3()
         self.__last_ir_value = '0'

      render = self.__font.render(txt, True, color)
      self.__txtRow(render, row=3)

   def __handleArm(self):
      txt = 'Arm: {}/{}'.format(self.__arm1, self.__arm2)
      color = LIGHT_GREEN

      render = self.__font.render(txt, True, color)
      self.__txtRow(render, row=7)

   def __handleCam(self):
      txt = 'Camera view'
      color = LIGHT_GREEN

      render = self.__font.render(txt, True, color)
      self.__txtRow(render, row=4)

   def __handleGear(self):
      txt = 'Gear: {}'.format(self.__gear)
      color = LIGHT_GREEN

      render = self.__font.render(txt, True, color)
      self.__txtRow(render, row=8)


   def __handlePower(self):
      try:
         val = float(self.__last_power_value)
      except:
         return
      ok = val > LOW_POWER
      txt = 'Low battery {:.2f}V'.format(val)
      color = RED if int(time.time()) % 2 == 0 else BLACK
      if ok:
         txt = 'Battery {:.2f}V'.format(val)
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
      self.__txtRow(render, row=4)

   def __handleDistance(self):
      try:
         val = int(self.__last_ir_value)
      except:
         return
      color = LIGHT_GREEN if val > MIN_DISTANCE else RED
      dist = int(val / 10) * '='
      render = self.__font.render('{} {}>|'.format(val, dist), True, color)
      self.__txtRow(render, row=10)

   def button(self, msg, x, y, w, h, ic, ac, action = None):
      mouse = pygame.mouse.get_pos()
      click = pygame.mouse.get_pressed()
      if x+w > mouse[0] > x and y+h > mouse[1] > y:
         pygame.draw.rect(self.__screen, ac,(x,y,w,h))

         if click[0] == 1 and action != None:
            action()         
      else:
         pygame.draw.rect(self.__screen, ic,(x,y,w,h))

      smallText = pygame.font.SysFont("comicsansms", 20)
      textSurf, textRect = text_objects(msg, smallText)
      textRect.center = ((x+(w/2)), (y+(h/2)) )
      self.__screen.blit(textSurf, textRect)

   def camView(self):
      frame = pygame.transform.rotate(self.__camViewFrame, self.__cam)
      self.__screen.blit(frame, (900, 300))

   def closeArm(self):
      self.__arm2 = 0
      arm2 = Cmd('arm2', self.__arm2, ARDUINO_CMD)
      self.__cmdTransport.send(arm2)

      self.__arm1 = 180
      arm1 = Cmd('arm1', self.__arm1, ARDUINO_CMD)
      self.__cmdTransport.send(arm1)

   def demo(self):
      cmd = [Cmd('speak', 'Hello, I am Curiosity mars rover', EV3_CMD),
             Cmd('speak', 'Drive forward', EV3_CMD),
             Cmd('drive', '0.3,0.3', EV3_CMD),
             Cmd('speak', 'Drive backward', EV3_CMD),
             Cmd('drive', '-0.3,-0.3', EV3_CMD),
             Cmd('speak', 'Stop', EV3_CMD),
             Cmd('drive', '0,0', EV3_CMD),

             Cmd('speak', 'Left', EV3_CMD),
             Cmd('turn', '-30', ARDUINO_CMD),

             Cmd('speak', 'Right', EV3_CMD),
             Cmd('turn', '30', ARDUINO_CMD),

             Cmd('speak', 'Forward', EV3_CMD),
             Cmd('turn', '0', ARDUINO_CMD),

             Cmd('speak', 'Laser on', EV3_CMD),
             Cmd('laser', '1', ARDUINO_CMD),

             Cmd('speak', 'Laser off', EV3_CMD),
             Cmd('laser', '0', ARDUINO_CMD),

             Cmd('speak', 'Hand close', EV3_CMD),
             Cmd('arm1', '170', ARDUINO_CMD),
             Cmd('arm2', '5', ARDUINO_CMD),

             Cmd('arm1', '90', ARDUINO_CMD),
             Cmd('arm2', '160', ARDUINO_CMD),

             Cmd('speak', 'Camera left', EV3_CMD),
             Cmd('cam', '-45', ARDUINO_CMD),

             Cmd('speak', 'Camera right', EV3_CMD),
             Cmd('cam', '45', ARDUINO_CMD),

             Cmd('speak', 'Camera forward', EV3_CMD),
             Cmd('cam', '0', ARDUINO_CMD),
      ]

      for c in cmd:
         self.__cmdTransport.send(c)
         pygame.display.flip()
         time.sleep(2)

      #self.__arm2 = 0
      #arm2 = Cmd('arm2', self.__arm2, ARDUINO_CMD)
      #self.__cmdTransport.send(arm2)

      #self.__arm1 = 180
      #arm1 = Cmd('arm1', self.__arm1, ARDUINO_CMD)
      #self.__cmdTransport.send(arm1)

   def shutdownBrick(self):
      cmd = Cmd('shutdown', 1, EV3_CMD)
      self.__cmdTransport.send(cmd)

   def __loop(self):

      ctrl = False
      while True:
         self.__screen.blit(self.__bkgnd_img, (0, 0))

         frame = self.__webFrame.getFrame()
         self.__screen.blit(frame, FRAME_POS)

         self.camView()

         self.__handleArm()
         self.__handleCam()
         self.__dispatchResponse()
         self.__handleDistance()
         self.__handlePing()
         self.__handlePower()
         self.__handleGear()
         #self.__joysticStatus()


         self.button('Close arm', 790, 100, 100, 30, GREEN, LIGHT_GREEN, self.closeArm)
         self.button('Demo', 900, 100, 100, 30, GREEN, LIGHT_GREEN, self.demo)
         self.button('Shutdown', 1010, 100, 100, 30, RED, RED, self.shutdownBrick)

         if self.__arm1 < 85:
            self.__arm1 = 85 
         if self.__arm1 > 170:
            self.__arm1 = 170

         if self.__arm2 < 5:
            self.__arm2 = 5
         if self.__arm2 > 175:
            self.__arm2 = 175

         if self.__cam < -85:
            self.__cam = -85 
         if self.__cam > 85:
            self.__cam = 85

         cmd = None
         for event in pygame.event.get():
            if event.type == pygame.QUIT:
               self.__webFrame.stop()
               self.__cmdTransport.stop()
               sys.exit()

            elif event.type == pygame.KEYUP:
               if event.key in [pygame.K_LEFT, pygame.K_RIGHT] and \
                  (not pygame.key.get_mods() & pygame.KMOD_CTRL) and \
                  (not pygame.key.get_mods() & pygame.KMOD_ALT):
                     cmd = Cmd('turn', 0, ARDUINO_CMD)
               elif event.key == pygame.K_SPACE:
                  self.__laser = 0
                  cmd = Cmd('laser', self.__laser, ARDUINO_CMD)
               elif event.key == pygame.K_UP:
                  cmd = Cmd('drive', '0,0', EV3_CMD)
               elif event.key == pygame.K_DOWN:
                  cmd = Cmd('drive', '0,0', EV3_CMD)
               elif event.key == pygame.K_1:
                  self.__gear = 1
                  cmd = Cmd('gear', '10', EV3_CMD)
               elif event.key == pygame.K_2:
                  self.__gear = 2
                  cmd = Cmd('gear', '7', EV3_CMD)
               elif event.key == pygame.K_3:
                  self.__gear = 3
                  cmd = Cmd('gear', '5', EV3_CMD)
               elif event.key == pygame.K_4:
                  self.__gear = 4
                  cmd = Cmd('gear', '3', EV3_CMD)
               elif event.key == pygame.K_5:
                  self.__gear = 5
                  cmd = Cmd('gear', '1', EV3_CMD)
            elif event.type in [pygame.KEYDOWN]:
               if event.key == pygame.K_ESCAPE:
                  self.__webFrame.stop()
                  self.__cmdTransport.stop()
                  sys.exit()
               elif event.key == pygame.K_SPACE:
                  self.__laser = 1
                  cmd = Cmd('laser', self.__laser, ARDUINO_CMD)
               elif pygame.key.get_mods() & pygame.KMOD_CTRL:
                  if event.key == pygame.K_LEFT:
                     self.__arm1 -= 5
                     cmd = Cmd('arm1', self.__arm1, ARDUINO_CMD)
                  elif event.key == pygame.K_RIGHT:
                     self.__arm1 += 5
                     cmd = Cmd('arm1', self.__arm1, ARDUINO_CMD)
                  elif event.key == pygame.K_UP:
                     self.__arm2 -= 5
                     cmd = Cmd('arm2', self.__arm2, ARDUINO_CMD)
                  elif event.key == pygame.K_DOWN:
                     self.__arm2 += 5
                     cmd = Cmd('arm2', self.__arm2, ARDUINO_CMD)
               elif pygame.key.get_mods() & pygame.KMOD_ALT:
                  if event.key == pygame.K_LEFT:
                     self.__cam += 5
                     cmd = Cmd('cam', self.__cam, ARDUINO_CMD)
                  elif event.key == pygame.K_RIGHT:
                     self.__cam -= 5
                     cmd = Cmd('cam', self.__cam, ARDUINO_CMD)
               else:
                  if event.key == pygame.K_LEFT:
                     cmd = Cmd('turn', -30, ARDUINO_CMD)
                  if event.key == pygame.K_RIGHT:
                     cmd = Cmd('turn', 30, ARDUINO_CMD)
                  if event.key == pygame.K_UP:
                     cmd = Cmd('drive', '0.3,0.3', EV3_CMD)
                  if event.key == pygame.K_DOWN:
                     cmd = Cmd('drive', '-0.3,-0.3', EV3_CMD)

            if cmd is not None:
               self.__cmdTransport.send(cmd)


         #data = self.__joystick.read()
         #for cmd in data:
         #   self.__cmdTransport.send(cmd)

         pygame.display.flip()
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
