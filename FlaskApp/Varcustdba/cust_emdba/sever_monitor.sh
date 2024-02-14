#!/bin/bash
x=1
x=`diff -qr /apps_autofs/recovery/ENTERPRISE/opsdba/emdba/sharedLogs/chkServers /tmp/chkServersBasic | wc -l`
echo " $x is the count "
date
if [ $x !=  0 ]
then

sleep 5

echo "Processing the file "
/usr/bin/python /var/cust_emdba/ServerMon.py >> ServerMon.txt

else
echo "The files have not changed so no need to process..."


fi
echo " Exiting server Monitoring process..."
date 
exit
~

