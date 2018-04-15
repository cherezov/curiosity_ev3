
echo "Arm1:177" | nc wrt 2000
echo "Arm2:0" | nc wrt 2000
sleep 3

var=177
while (($var>=90));
do
   echo "Arm1:$var" | nc wrt 2000
   sleep 0.1
   var=$(expr $var - 30)
done
sleep 4

var=10
while (($var<140));
do
   echo "Arm2:$var" | nc wrt 2000
   sleep 0.1
   var=$(expr $var + 5)
done

echo "arm:2000" | nc wrt 88 # open
sleep 2
echo "arm:-2000" | nc wrt 88 # close

sleep 2
echo "Arm2:0" | nc wrt 2000
sleep 1
echo "Arm1:177" | nc wrt 2000
