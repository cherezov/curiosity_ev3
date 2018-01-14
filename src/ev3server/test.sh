echo "speak:starting self test" | nc wrt 88
sleep 3

echo "speak:led is red" | nc wrt 88
sleep 3

echo "led:red" | nc wrt 88
sleep 1

echo "speak:led is orange" | nc wrt 88
sleep 3
echo "led:orange" | nc wrt 88
sleep 1

echo "speak:led is yellow" | nc wrt 88
sleep 3
echo "led:yellow" | nc wrt 88
sleep 1

echo "speak:led is green" | nc wrt 88
sleep 3
echo "led:green" | nc wrt 88
sleep 1

echo "speak:drive forward test" | nc wrt 88
sleep 3
echo "drive:0.3;0.3" | nc wrt 88
sleep 5

echo "speak:drive backward test" | nc wrt 88
sleep 3
echo "drive:-0.3;-0.3" | nc wrt 88
sleep 5

echo "speak:stop engine test" | nc wrt 88
sleep 3
echo "drive:0;0" | nc wrt 88
sleep 2

echo "speak:arm one test" | nc wrt 88
sleep 3
echo "Arm1:160" | nc wrt 2000
sleep 1
echo "Arm1:90" | nc wrt 2000
sleep 1

echo "speak:arm two test" | nc wrt 88
sleep 3
echo "Arm2:0" | nc wrt 2000
sleep 1
echo "Arm2:170" | nc wrt 2000
sleep 1
echo "Arm2:90" | nc wrt 2000
sleep 1

echo "speak:camera rotation test" | nc wrt 88
sleep 3
echo "Cam:10" | nc wrt 2000
sleep 1
echo "Cam:-3" | nc wrt 2000
sleep 1
echo "Cam:0" | nc wrt 2000
sleep 2

echo "speak:laser test" | nc wrt 88
sleep 3
echo "Laser:1" | nc wrt 2000
sleep 1
echo "Laser:0" | nc wrt 2000
sleep 1
echo "Laser:1" | nc wrt 2000
sleep 1
echo "Laser:0" | nc wrt 2000
sleep 1

echo "speak:turn left test" | nc wrt 88
sleep 3
echo "left:45" | nc wrt 2000
sleep 1
echo "speak:turn right test" | nc wrt 88
sleep 3
echo "right:45" | nc wrt 2000
sleep 1
echo "right:0" | nc wrt 2000
sleep 1

echo "speak:self test complete" | nc wrt 88
