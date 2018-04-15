#include <Servo.h> //используем библиотеку для работы с сервоприводом

int leftWheelPin = 9;
int rightWheelPin = 10;
int camPin = 6;
int laserPin = 13;
int arm1Pin = 11;
int arm2Pin = 3;


Servo servoLW; //объявляем переменную servo типа Servo
Servo servoRW; //объявляем переменную servo типа Servo
Servo servoCam; //объявляем переменную servo типа Servo
Servo servoArm1;
Servo servoArm2;

void setup() //процедура setup
{
  servoLW.attach(leftWheelPin); //привязываем привод к порту 10
  servoRW.attach(rightWheelPin); //привязываем привод к порту 10
  servoCam.attach(camPin); //привязываем привод к порту 10
  servoArm1.attach(arm1Pin);
  servoArm2.attach(arm2Pin);
  
  Serial.begin(115200);
  while (!Serial)
  {
     // wait for serial port to connect. Needed for native USB port only
  }
}

const int CMD_MAX_LEN = 16;

char ch;
char cmd[CMD_MAX_LEN] = {0};
char val[CMD_MAX_LEN] = {0};
char* it = cmd;

void reset()
{
  for (int i = 0; i < CMD_MAX_LEN; ++i)
  {
    cmd[i] = 0;
    val[i] = 0;
  }
  it = cmd;
}

/// @brief Read command 'cmd:val;'
bool read_command()
{
  ch = Serial.read();
  if (ch == '\n')
  {
    // just skip it
  }
  else if (ch == ':')
  {
    it = val;
  }
  else if (ch == ';' || ch == -1)
  {
    return true;
  }
  else
  {
     *it = ch;
      ++it;
  }

  return false;
}

bool is_cmd(const char* c)
{
  return strcmp(cmd, c) == 0;
}

void loop() //процедура loop
{
  if (!Serial.available() || !read_command())
  {
    return;
  }

  if (is_cmd("arm1"))
  {
    const int value = atoi(val);
    servoArm1.write(value);    
  }
  else if (is_cmd("arm2"))
  {
    const int value = atoi(val);
    servoArm2.write(value);    
  }
  else if (is_cmd("turn"))
  {
    const int value = (atoi(val) + 90) % 180;
    Serial.write(val);
    Serial.println(atoi(val));
    Serial.println(value);
    servoLW.write(value);    
    servoRW.write(value);    
  }
  else if (is_cmd("cam"))
  {
    const int value = (atoi(val) + 90) % 180;
    Serial.write(val);
    Serial.println(atoi(val));
    Serial.println(value);
    servoCam.write(value);    
  }
  else if (is_cmd("ping"))
  {
    Serial.write(val);
  }
  else if (is_cmd("laser"))
  {
    const int value = atoi(val);
    if (value == 0)
    {
      analogWrite(laserPin, 0);
    }
    else
    {
      analogWrite(laserPin, 256);
    }
  }
 
  reset(); 
}
