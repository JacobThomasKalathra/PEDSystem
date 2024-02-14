#!/usr/bin/python

"""
Usage : python <script name>
Remote fetch all  error logs  filer from emdba server to local
Parse each report file and insert data into DB after cleanup
Script to be executed by a cron

"""

import glob, os, shutil
import re
import sys
import yaml
import logging
import paramiko
import cx_Oracle


from datetime import datetime

# Modify path variable to include custom libraries
sys.path.append(os.path.join(sys.path[0],'lib'))

# Import custom module for Oracle DB Connection
from connect_db import OracleDB

# Read yml conf file to get configuration parameters
with open(os.path.join(os.path.dirname(__file__),'conf/emdba_conf.yml'), 'r') as file:
    conf = yaml.load(file)

# Global Variables
emdba_host = conf["emdba_details"]["host"]      # Emdba remote server
emdba_user = conf["emdba_details"]["username"]  # Emdba server username
emdba_password = conf["emdba_details"]["password"]  # Emdba server Password
remote_dir = conf["emdba_details"]["remote_dir"]# Remote server directory 
tmp_dir = conf["emdba_details"]["tmp_dir"]   # Local tmp directory to store Report_*.out files
log_path = conf["emdba_details"]["log_path"]  # Log file path

print("Emdba remote server  " + emdba_host)

print("Emdba server username  " + emdba_user)

print("Emdba server Password  " + emdba_password)

print("Remote server directory  " + remote_dir)

print("Local tmp directory   " + tmp_dir)

print("Log file path " + log_path)
log_path = log_path +"_ServerMon"

if not remote_dir.endswith('/'):
    remote_dir = remote_dir + '/'
    remote_dir = remote_dir[0:-8]
    remote_dir = remote_dir+"chkServers"
    print("Remote server directory adding / : " + remote_dir)

report_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Emdba reportfile-dbtable mapping
emdba_table_map = {'chkServersBasic_*.Error':'PSFT_ERRORFILE_LOG'}

# Logging Configurations. Set level=logging.DEBUG to log all messages.
logging.basicConfig(filename=log_path, filemode='a', format='%(asctime)s - %(levelname)s- %(message)s', datefmt='%d-%b-%y %H:%M:%S',level=logging.DEBUG)

# Start logging
logging.info('######## LOG START - SERVER MONITOR  %s ############\n',report_time)


def exit_handler():
    """"invoke on all abnormal exit"""

    # End logging
    logging.info('######## LOG END SERVER MONITOR ############\n\n')
    sys.exit(1)
	

def remote_fetch_operations():

        """To fetch  files from remote emdba server to local"""
        
        # In emdba server,search for directories with pattern 'chkServersBasic*' under basedir
  	pattern = '"chkServersBasic*"'
        
        def ld(val):
            return next(os.walk(val))[1]
        def FileCheck(fn):
    	    try:
              file = open(fn, "r")
              content = file.read()
              val=int(content.strip())
              return val
            except IOError:
              print "Error: File does not appear to exist."
              return 0
        def get_log(logfile):
            pathfile= logfile +".Error" 
            os.system("cat " +pathfile+" > merged.txt")
            f = open("merged.txt", "r")
            text1 = f.read()
            slice_object = slice(3750)
            	 
            f.close() 
            res = text1[slice_object]
            return res

        #print("Remote server directory inside fun remote_fetch_operations  " + remote_dir)
        dest = '/tmp/chkServersBasic'
        if os.path.exists(dest):
    	   shutil.rmtree(dest)
        destination= shutil.copytree(remote_dir, dest)
        os.system("ls  " + dest+ "/summary/*.Error | sed -e 's/\..*$//' > Logfile.txt")
        # Establish database connection
    	logging.info('Connecting to DB...')
    	# Create an object of DB Wrapper Class
    	db = OracleDB()

        try:
	    cur = db.connect()
            cur.execute("select * from PSFT_ERRORFILE_LOG")
            data=cur.fetchall()
            print("cur.rowcount1 " , len(data))

            if len(data)==0:
               merror = FileCheck(dest+"/same_error_count")
               print("same_error_count",merror)
                
                #Logfile = os.system("ls /tmp/Jacob/summary/*.Error | sed -e 's/\..*$//' > Logfile.txt")
               with open('Logfile.txt') as f:
                  my_list = [x.rstrip() for x in f]
                  #print(my_list)
               prev_filename=cur_filename=prev_content=cur_content=""
               prev_sameerror=cur_sameerror=0
               cnt = 1
               db.disconnect()
            else:
               PSFT_ERRORFILE_LOG_ERR_DATE = None
    	       PSFT_ERRORFILE_LOG_LOG_CONTENT = None
               PSFT_ERRORFILE_LOG_ERR_COUNT = 0
               sql_cnt = ('select ERR_DATE,LOG_CONTENT,ERR_COUNT '
        	      'from PSFT_ERRORFILE_LOG '
        	      'order by err_date desc ')
	       cur.execute(sql_cnt)
               rows = cur.fetchmany(1)
               print("cur.rowcount2 " , cur.rowcount)


               for row in rows:
                   #print(row)
	           break
	        
	       
 
               # Destination path
                
               PSFT_ERRORFILE_LOG_ERR_DATE = row[0]
               PSFT_ERRORFILE_LOG_LOG_CONTENT = row[1]
               PSFT_ERRORFILE_LOG_ERR_COUNT = row[2]
               print("The  row has  ",PSFT_ERRORFILE_LOG_ERR_DATE,PSFT_ERRORFILE_LOG_LOG_CONTENT,PSFT_ERRORFILE_LOG_ERR_COUNT)
                
               a_file = open('Logfile.txt', 'r')
    	            #lines = f.readlines()
               line_number = 0   
               for number,line in enumerate(a_file):
                  if PSFT_ERRORFILE_LOG_ERR_DATE in line:
                     line_number = number
                     #print("Found it! " , line_number)
                  else:
                     pass
               with open('Logfile.txt', 'r') as fp:
                  cols = []
                  lpst = list()
                  for i, line in enumerate(fp):
                     if i > line_number :
                      # print("Next " , line[:60:])
                       logging.info(' Insert new rows  to table..')
                       cols = line[:60:]
                       lpst.append(cols)
                  #print(lpst)
                  my_list = lpst
                     
                  
               prev_filename=cur_filename=prev_content=cur_content=""
               prev_sameerror=cur_sameerror=0
               cnt = 2
               prev_filename = PSFT_ERRORFILE_LOG_ERR_DATE
               prev_content = PSFT_ERRORFILE_LOG_LOG_CONTENT
               prev_sameerror= PSFT_ERRORFILE_LOG_ERR_COUNT
               #logging.debug('%s table is not empty ',cur.rowcount)
               db.disconnect()
            
               
        
            #data_dict = {}
            logging.info(' Insert Fresh Row to table..')
            db = OracleDB()
            try:
                cur = db.connect()
            except Exception as error:
                logging.error('%s\nError in database connection..Exiting',error)
                exit_handler()
            
            sql = ('insert into PSFT_ERRORFILE_LOG(ERR_DATE, LOG_CONTENT, ERR_COUNT) '
                 'values(:ERR_DATE,:LOG_CONTENT,:ERR_COUNT)')
            sql1 =  ('update PSFT_ERRORFILE_LOG '
        		'set ERR_COUNT = -1 '
                         'where ERR_DATE = :PREV_DATE1')
            sql2 =  ('delete from  PSFT_ERRORFILE_LOG where ERR_COUNT=-1')

            for x in my_list:
                x = x.rstrip()
                cur_filename=x[45:61:] 
                cur_content =get_log(x)
                ERR_DATE = cur_filename
                LOG_CONTENT = cur_content

                if cnt == 1 :
                  ERR_COUNT = prev_sameerror= 1
                  cur.execute(sql, [ERR_DATE, LOG_CONTENT, ERR_COUNT])
                  prev_filename = cur_filename
                  prev_content = cur_content
                  print(cur_filename)
                  print(cur_content)
                  cnt =cnt +1
                  
                else :
                  
                  if cur_content == prev_content:
                      PREV_DATE1 = prev_filename
                      cur_sameerror = prev_sameerror+1
                      cur.execute(sql1, [PREV_DATE1])

                  else:
                      cur_sameerror =1
                  ERR_COUNT = cur_sameerror
                  cur.execute(sql, [ERR_DATE, LOG_CONTENT, ERR_COUNT])
                  prev_filename = cur_filename
                  prev_content = cur_content
                  prev_sameerror = cur_sameerror          

                  print(cur_filename)
                  print(cur_content)
                  cnt =cnt +1
            cur.execute(sql2) 
            db.disconnect()    
                
            #print(data_dict.values())
            #print(data_dict.keys())
            #print(len(data_dict.keys()))

                
	    #print("PSFT_ERRORFILE_LOG table is empty ",cur.rowcount)
        except cx_Oracle.DatabaseError as e:
            print("There is a problem with Oracle", e)
            db.disconnect()
        





        

if __name__ == '__main__':
  
   remote_fetch_operations()
   exit_handler()

logging.info('######## LOG END ############\n\n')


