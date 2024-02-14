#!/bin/bash
x=1
date
x=`diff -qr /apps_autofs/recovery/ENTERPRISE/opsdba/emdba/sharedLogs/chkServers  /var/www/FlaskApp/FlaskApp/ServerMon/chkServers | wc -l`
echo " $x is the count "
if [ $x !=  0 ]
then
sleep 10 
echo "Processing the file "
/usr/bin/python /var/cust_emdba/ServerMon.py >> ServerMon.txt
 
cp -R  /apps_autofs/recovery/ENTERPRISE/opsdba/emdba/sharedLogs/chkServers/* /var/www/FlaskApp/FlaskApp/ServerMon/chkServers
echo " The file has been copied " >> ServerMon.txt
 
else
 
echo "The files have not changed so no need to process..."
 
 
 
 
fi
echo " Exiting server Monitoring process..."
date
exit
