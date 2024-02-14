#!/usr/bin/python

"""
Usage : python <script name>
Remote fetch all Summary.out files from emdba server to local
Parse each report file and insert data into DB after cleanup
Script to be executed by a cron

Change log:
03/25/2021 : Jacob
           - Initial Version
"""

import glob, os, shutil
import re
import sys
import yaml
import logging
#import paramiko
import cx_Oracle


from datetime import datetime

# Modify path variable to include custom libraries
sys.path.append(os.path.join(sys.path[0],'lib'))

# Import custom module for Oracle DB Connection
#from connect_db import OracleDB

dsnStr = cx_Oracle.makedsn("slc10ger.us.oracle.com", "1521", "CADEVDB")
con = cx_Oracle.connect(user="invdev",password="invdev",dsn=dsnStr)
cur = con.cursor()
cur2 = con.cursor()


# Read yml conf file to get configuration parameters
with open(os.path.join(os.path.dirname(__file__),'conf/emdba_conf.yml'), 'r') as file:
    conf = yaml.load(file)

# Global Variables
emdba_host = conf["summaryRep_details"]["host"]      # Emdba remote server
emdba_user = conf["summaryRep_details"]["username"]  # Emdba server username
emdba_password = conf["summaryRep_details"]["password"]  # Emdba server Password
remote_dir = conf["summaryRep_details"]["remote_dir"]# Remote server directory 
tmp_dir = conf["summaryRep_details"]["tmp_dir"]   # Local tmp directory to store Report_*.out files
log_path = conf["summaryRep_details"]["log_path"]  # Log file path

print("Emdba remote server  " + emdba_host)

print("Emdba server username  " + emdba_user)

print("Emdba server Password  " + emdba_password)

print("Remote server directory  " + remote_dir)

print("Local tmp directory   " + tmp_dir)

print("Log file path " + log_path)

if not remote_dir.endswith('/'):
    remote_dir = remote_dir + '/'
    print("Remote server directory adding /  " + remote_dir)

report_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Emdba reportfile-dbtable mapping
emdba_table_map = {'summaryReport.ped':'PED_SERVER_DETAIL'}

# Logging Configurations. Set level=logging.DEBUG to log all messages.
logging.basicConfig(filename=log_path, filemode='a', format='%(asctime)s - %(levelname)s- %(message)s', datefmt='%d-%b-%y %H:%M:%S',level=logging.DEBUG)

# Start logging
logging.info('######## LOG START ############\n')


def exit_handler():
    """"invoke on all abnormal exit"""

    # End logging
    logging.info('######## LOG END ############\n\n')
    sys.exit(1)
def cleanup_emdba_tables():
    """Perform emdba tables data cleanup"""

    # Establish database connection
    logging.info('Connecting to DB...')
    
    try:
        cur = con.cursor()
        
    except Exception as error:
        logging.error('%s\nError in database connection..Exiting',error)
        exit_handler()
    # Successful DB Connection
    logging.info('Successfully established DB Connection')

    for each_table in emdba_table_map.values():
        # Cleanup existing table entries
        logging.info('Deleting entries from table %s',each_table)
        query = 'DELETE from {tablename}'.format(tablename=each_table)
        try:
          cur.execute(query)
          logging.debug('%s rows deleted',cur.rowcount)
        except cx_Oracle.DatabaseError as e:
          logging.debug('%s',e)
    #Disconnect database
    logging.info("Disconnecting DB")
    cur.close()


def populate_emdba_tables():
    """Parse report files and insert data into emdba tables """

    # Establish database connection
    logging.info('Connecting to DB...')
    
    try:
        cur2 = con.cursor()
    except Exception as error:
        logging.error('%s\nError in database connection..Exiting',error)
        exit_handler()

    # Successful DB Connection
    logging.info('Successfully established DB in populate_emdba_tables()')

    #Referring variable in outer scope
    global report_time

    # Parse each .out file row by row
    for each_out_file in os.listdir(tmp_dir):
        result = []
        cols = []
        skip_cols = []
        query = None
        logging.debug('Parsing %s file.......',each_out_file)

        # Get full path of file
        tmp_out_file = os.path.join(tmp_dir,each_out_file) 
        fp = open(tmp_out_file, "rb")
        lines = fp.readlines()

        # If summaryReport.ped file,split on '_' and insert all values
    if re.search( "summaryReport.ped", each_out_file):
        logging.debug('inside rematch ')
        for line in lines:
                cols = line.rstrip().split("_")
                #print("column value   " , cols)
                #logging.debug('inside rematch ',cols)
		#cols.append(report_time)
                result.append(tuple(cols))
                query='INSERT INTO {tablename} (HOST_NAME1, UPTIME1, SYSLOAD1, VM_R, VM_B, VM_WA, VM_SWPD, IOSTAT, DEFUNCT, DBSTAT_ALL, DBSTAT_UP, DBSTAT_DOWN, DBSTAT_SKIP, LASTUPDATE) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14)'.format(tablename=emdba_table_map[each_out_file])
               
                #query='INSERT INTO {tablename} (HOST_NAME, UPTIME, SYSLOAD, VM_R, VM_B, VM_WA, VM_SWPD, IOSTAT, DEFUNCT, DBSTAT_ALL, DBSTAT_UP, DBSTAT_DOWN, DBSTAT_SKIP, LASTUPDATE) VALUES ('slcaa697.us.oracle.com', 'up 31 days 20:47', '0.03, 0.10, 0.08', '0', '0', '0', '0', '0.06', '4', '4', '0', '0','0',TO_TIMESTAMP('20:12:40-05-04-2021', 'HH24:MI:SS-DD/MM/YYYY')'.format(tablename=emdba_table_map[each_out_file])          
     
        # Try pushing data if not empty
    if result:	
            try:
                logging.info('Inserting data into %s table',emdba_table_map[each_out_file])
                # Batch Insertion for faster performance
                cur2.executemany(query,result)
                logging.debug('%s rows inserted',cur2.rowcount)
            except cx_Oracle.DatabaseError as e:
                logging.debug('%s',e)
                # Database rollback to avoid inconsistency
                logging.info('Performing database roll back')
                #cleanup_emdba_tables()
                #db.disconnect()
                cur2.close()
                con.commit()
                
                    
    #Disconnect database
    logging.info("Disconnecting DB in populate_emdba_tables()")
    con.commit()
    con.close()



def remote_fetch_operations():

    """To fetch summaryReport.ped files from remote emdba server """
    
    
    def ld(val):
        return next(os.walk(val))[1]

    print("Remote server directory inside   " + remote_dir)
    
    namedir='summaryReport.ped'
    print ("picked file for transfer : " + str(namedir))

    
    logging.debug('Directory is Jacob %s',namedir)

  
    logging.info('Getting Summary Report under %s ',remote_dir)
    
    dest_dir = tmp_dir
    print("Destination Dir " + tmp_dir)
    sour_dir = remote_dir+namedir 
    print ("Source Dir " + sour_dir)
     
    logging.info(' Summary Report under %s ',sour_dir)
    print(remote_dir)
    os.chdir(remote_dir)
    num = 0 
    for file in glob.glob("*Report*"):
            print(file)
            num=num +1 
            
    print ("Number of Files "+str(num)) 
    if num > 0:
        logging.info('Deleting temp directory %s',tmp_dir)
        shutil.rmtree(tmp_dir,ignore_errors=True)
    
        # Create a local tmp folder to store report.out files
        logging.info('Creating temp directory %s',tmp_dir)
        try:
          os.mkdir(tmp_dir)
        except OSError as e:
          logging.error('%s',e)
          exit_handler()
    	for file in glob.glob("*Report*"):
            shutil.copy(file, dest_dir)
        logging.info('######## exit_handler end ############\n\n')    
        # exit_handler()
    else:
        logging.error('No SummaryReport files present under %s',sour_dir)
        exit_handler()
    
  # Perform database cleanup
    #logging.info('Calling cleanup_emdba_tables()')
    #cleanup_emdba_tables()
     

  #  Inserting new data into emdba tables
    logging.info('Calling populate_emdba_tables()')
    populate_emdba_tables()  
    exit_handler() 

if __name__ == '__main__':
   remote_fetch_operations()

logging.info('######## LOG END ############\n\n')






