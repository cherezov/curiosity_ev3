# @file ev3client.py
# @author Pavel Cherezov (cherezov.pavel@gmail.com)

import io
import socket,sys
import pygame
from urllib.request import urlopen
import socket

GATE_IP = "192.168.1.120"
GATE_PORT= 88
FRAME_PORT = 8080

def getFrame(ip, port):
   try:
      frame_url = 'http://{}:{}/?action=snapshot'.format(ip, port)
      image_str = urlopen(frame_url).read()
      image_file = io.BytesIO(image_str)

      frame = pygame.image.load(image_file)
   except:
      frame = pygame.image.load("../../images/noise.jpg")
      frame = pygame.transform.scale(frame, (640, 480))
   return frame

def initScreen():
   pygame.init()
   screen = pygame.display.set_mode((1000,600))
   pygame.display.set_caption('Robot controller')

   bg = pygame.image.load("../../images/bkgnd/tunnel.jpg")
   screen.blit(bg, (0, 0))
   return screen

def initJoiystick():
   pygame.joystick.init()
   if pygame.joystick.get_count() == 0:
      return None

   joystickId = 0
   joystick = pygame.joystick.Joystick(joystickId)
   joystick.init()
   return joystick

def connectToBrick(ip, port):
   try:
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.connect((ip, port))
      return s
   except:
      return None

prev_x = 0
prev_y = 0

def handleJoystick():
   if joystick is None:
      return ''
   global prev_x, prev_y
   dataToSend = ''
   axes = joystick.get_numaxes()

   x = joystick.get_axis(0) * 10
   y = joystick.get_axis(1) * 10

   if prev_x != x and prev_y != y:
      dataToSend = 'xy:{};{}'.format(int(x), int(y))
      prev_x = x
      prev_y = y

   buttons = joystick.get_numbuttons()
   for i in range( buttons ):
      if i == 0:
         button = joystick.get_button( i )
         if button == 1:
            dataToSend = 'speak:ho ho ho'
   return dataToSend

if __name__ == '__main__':
   screen = initScreen()
   clock = pygame.time.Clock()

   joystick = initJoiystick()
   jsBtn = pygame.Color('green') if joystick is not None else pygame.Color('red')
   pygame.draw.rect(screen, jsBtn, (750,120,100,50))

   brickSock = connectToBrick(GATE_IP, GATE_PORT)
   brickBtn = pygame.Color('green') if brickSock is not None else pygame.Color('red')
   pygame.draw.rect(screen, brickBtn, (750,220,100,50))

   while True:
      frame = getFrame(GATE_IP, FRAME_PORT)
      screen.blit(frame, (40, 120))

      pygame.display.flip()
      dataToSend = handleJoystick()
      if dataToSend and brickSock is not None:
         brickSock.sendall(dataToSend.encode())

      for event in pygame.event.get():
         if event.type == pygame.QUIT:
            brickSock.close()
            sys.exit()

      clock.tick(60)

