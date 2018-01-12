echo "led:yellow" | nc wrt 88
scp ev3server.cfg root@192.168.1.120:ev3server.update
echo "led:red" | nc wrt 88
scp ev3server.py root@192.168.1.120:ev3server.update
echo "led:yellow" | nc wrt 88
scp ev3server.daemon.py root@192.168.1.120:ev3server.update
echo "led:red" | nc wrt 88
scp daemon.py root@192.168.1.120:ev3server.update
echo "led:yellow" | nc wrt 88

echo "update:" | nc wrt 88
echo "restart:" | nc wrt 88
