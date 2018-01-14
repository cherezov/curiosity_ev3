#include <Servo.h> //используем библиотеку для работы с сервоприводом

int leftWheelPin = 9;
int rightWheelPin = 10;
int camPin = 6;
int laserPin = 12;
int armClosePin = 13;
int armLongPin = 14;


Servo servoLW; //объявляем переменную servo типа Servo
Servo servoRW; //объявляем переменную servo типа Servo
Servo servoCam; //объявляем переменную servo типа Servo

void setup() //процедура setup
{
  servoLW.attach(leftWheelPin); //привязываем привод к порту 10
  servoRW.attach(rightWheelPin); //привязываем привод к порту 10
  servoCam.attach(camPin); //привязываем привод к порту 10
  
  Serial.begin(115200);
  while (!Serial) {
    ; // wait for serial port to connect. Needed for native USB port only
  }
}

void loop() //процедура loop
{
  if (!Serial.available())
  {
    return;
  }

  char cmd[64] = {0};
  Serial.readBytesUntil(';', cmd, 64);
 
    Serial.write(cmd);
 
  if (strcmp(cmd, "test") == 0)
  {
    Serial.write("test ok");
    servoLW.write(10);
  } 
  else if (strcmp(cmd, "LW0") == 0)
  {
    Serial.println("left wheel 0");
    servoLW.write(10);
  } 
  else if (strcmp(cmd, "LW45") == 0)
  {
    Serial.println("left wheel 45");
    servoLW.write(45);
  } 
  else if (strcmp(cmd, "LW90") == 0)
  {
    Serial.println("left wheel 90");
    servoLW.write(90);
  } 
  else if (strcmp(cmd, "LW135") == 0)
  {
    Serial.println("left wheel 135");
    servoLW.write(135);
  } 
  else if (strcmp(cmd, "LW180") == 0)
  {
    Serial.println("left wheel 180");
    servoLW.write(170);
  } 
  
  else if (strcmp(cmd, "RW0") == 0)
  {
    Serial.println("right wheel 0");
    servoRW.write(10);
  } 
  else if (strcmp(cmd, "RW45") == 0)
  {
    Serial.println("right wheel 45");
    servoRW.write(45);
  } 
  else if (strcmp(cmd, "RW90") == 0)
  {
    Serial.println("right wheel 90");
    servoRW.write(90);
  } 
  else if (strcmp(cmd, "RW135") == 0)
  {
    Serial.println("right wheel 135");
    servoRW.write(135);
  } 
  else if (strcmp(cmd, "RW180") == 0)
  {
    Serial.println("right wheel 180");
    servoRW.write(170);
  }   
  
  else if (strcmp(cmd, "Cam0") == 0)
  {
    Serial.println("camera 0");
    servoCam.write(10);
  } 
  else if (strcmp(cmd, "Cam45") == 0)
  {
    Serial.println("camera 45");
    servoCam.write(45);
  } 
  else if (strcmp(cmd, "Cam90") == 0)
  {
    Serial.println("camera 90");
    servoCam.write(90);
  } 
  else if (strcmp(cmd, "Cam135") == 0)
  {
    Serial.println("camera 135");
    servoCam.write(135);
  } 
  else if (strcmp(cmd, "Cam180") == 0)
  {
    Serial.println("camera 180");
    servoCam.write(170);
  }
  Serial.readBytesUntil('\n', cmd, 64);

  //servo.write(20); //ставим вал под 0
  delay(2000); //ждем 2 секунды
}
