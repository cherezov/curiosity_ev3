echo 1
echo "led:yellow" | nc wrt 88
echo 2
scp ev3server.cfg root@192.168.1.120:ev3server.update
echo 3
echo "led:red" | nc wrt 88
echo 4
scp ev3server.py root@192.168.1.120:ev3server.update
echo 5
echo "led:yellow" | nc wrt 88
echo 6
scp ev3server.daemon.py root@192.168.1.120:ev3server.update
echo 7
echo "led:red" | nc wrt 88
echo 8
scp daemon.py root@192.168.1.120:ev3server.update
echo 9
scp daemon.py root@192.168.1.120:ev3server.update
echo 10 
echo "led:yellow" | nc wrt 88
echo 11 

echo "update:" | nc wrt 88
echo 12 
echo "restart:" | nc wrt 88
echo 13 
