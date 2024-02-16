#!/usr/bin/python

"""
Usage : python <script name>
Remote fetch all Report_*.out files from emdba server to local
Parse each report file and insert data into DB after cleanup
Script to be executed by a cron

Change log:
03/07/2019 
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

if not remote_dir.endswith('/'):
    remote_dir = remote_dir + '/'
    print("Remote server directory adding /  " + remote_dir)

report_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Emdba reportfile-dbtable mapping
emdba_table_map = {'Report_Environments.out':'INV_EMDBA_ENV',
                   'Report_Error.out':'INV_EMDBA_ERROR',
                   'Report_Skipped.out':'INV_EMDBA_SKIP',
                   'Report_Blackout.out':'INV_EMDBA_BLACKOUT',
                   'Report_Locked.out':'INV_EMDBA_LOCK'}

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
    # Create an object of DB Wrapper Class
    db = OracleDB()
    # Connect to DB
    try:
        cur = db.connect()
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
    db.disconnect()


def populate_emdba_tables():
    """Parse report files and insert data into emdba tables """

    # Establish database connection
    logging.info('Connecting to DB...')
    # Create an object of DB Wrapper Class
    db = OracleDB()
    # Connect to DB
    try:
        cur = db.connect()
    except Exception as error:
        logging.error('%s\nError in database connection..Exiting',error)
        exit_handler()

    # Successful DB Connection
    logging.info('Successfully established DB Connection')

    #Referring variable in outer scope
    global report_time

    # Parse each .out file row by row
    for each_out_file in os.listdir(tmp_dir):
        result = []
        cols = []
        skip_cols = []
        query = None
        logging.debug('Parsing %s file',each_out_file)

        # Get full path of file
        tmp_out_file = os.path.join(tmp_dir,each_out_file) 
        fp = open(tmp_out_file, "rb")
        lines = fp.readlines()

        # If Report_Blackout.out file,line split not required
        if re.match( r'\w+\_Blackout\.out', each_out_file):
            for line in lines:
                line = line.rstrip()
                # Report time is appended to each row
                cols =[line,report_time] 
                result.append(tuple(cols))
            query='INSERT INTO {tablename} (DBSERVER,REP_TIMESTAMP) VALUES (:1, :2)'.format(tablename=emdba_table_map[each_out_file])
        # If Report_Environments.out file,split on ':' and insert all values
        elif re.match( r'\w+\_Environments\.out', each_out_file):
            for line in lines:
                cols = line.rstrip().split(":")
                cols.append(report_time)
                result.append(tuple(cols))
                query='INSERT INTO {tablename} (DBSERVER,DB_TYPE,DBNAME,SLOT,DBOWNER,ORACLE_VERSION,DB_CREATION_DT,LAST_ACCESS_DATE,APPLICATION,TOOLS_MAJ_VERSION,TOOL_PTCH_VERSION,DB_CHAR,PATCH,STATUS,REP_TIMESTAMP) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14, :15)'.format(tablename=emdba_table_map[each_out_file])
            #query='INSERT INTO {tablename} (DBSERVER,DBNAME,SLOT,DBOWNER,ORACLE_VERSION,DB_CREATION_DT,LAST_ACCESS_DATE,APPLICATION,TOOLS_MAJ_VERSION,TOOL_PTCH_VERSION,DB_CHAR,DB_TYPE,PATCH,STATUS,REP_TIMESTAMP) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14,:15)'.format(tablename=emdba_table_map[each_out_file])
        # If Report_Error.out file,split on ':' but insert only first 3 values
        elif re.match( r'\w+\_Error\.out', each_out_file):
            for line in lines:
                cols = line.rstrip().split(":")[:3]
                cols.append(report_time)
                result.append(tuple(cols))
            query ='INSERT INTO {tablename} (DBSERVER,DBNAME,SLOT,REP_TIMESTAMP) VALUES (:1, :2, :3, :4)'.format(tablename=emdba_table_map[each_out_file])
        # If Report_Skipped.out file,split on ':' but insert only first(oraslot) and last(hostname) values
        elif re.match( r'\w+\_Skipped\.out', each_out_file):
            for line in lines:
                skip_cols = line.rstrip().split(":")
                cols = [skip_cols[-1],skip_cols[0],report_time]
                #cols = [x.strip(' ') for x in cols]
                result.append(tuple(cols))
            query ='INSERT INTO {tablename} (DBSERVER,SLOT,REP_TIMESTAMP) VALUES (:1, :2, :3)'.format(tablename=emdba_table_map[each_out_file])
	# If Report_Locked.out file,split on ':' but insert only first(oraslot) and last(hostname) values
	elif re.match( r'\w+\_Locked\.out', each_out_file):
	     for line in lines:
	         skip_cols = line.rstrip().split(":")
	         cols = [skip_cols[-1],skip_cols[0],report_time]
	         #cols = [x.strip(' ') for x in cols]
	         result.append(tuple(cols))
             query ='INSERT INTO {tablename} (DBSERVER,SLOT,REP_TIMESTAMP) VALUES (:1, :2, :3)'.format(tablename=emdba_table_map[each_out_file])        
        # Try pushing data if not empty
        if result:	
            try:
                logging.info('Inserting data into %s table',emdba_table_map[each_out_file])
                # Batch Insertion for faster performance
                cur.executemany(query,result)
                logging.debug('%s rows inserted',cur.rowcount)
            except cx_Oracle.DatabaseError as e:
                logging.debug('%s',e)
                # Database rollback to avoid inconsistency
                logging.info('Performing database roll back')
                cleanup_emdba_tables()
                db.disconnect()
                exit_handler()
                    
    #Disconnect database
    logging.info("Disconnecting DB")
    db.disconnect()


def remote_fetch_operations():

    """To fetch Report.out files from remote emdba server to local"""
    
    # In emdba server,search for directories with pattern 'Report_*' under basedir
    pattern = '"Report_*"'
    
    def ld(val):
        return next(os.walk(val))[1]

    #print("Remote server directory inside fun remote_fetch_operations  " + remote_dir)
    tuple_list = []
    for index in ld(remote_dir):
        tuple_list.append(index)
    print("Tuple list")
    print(tuple_list[-1])
    namedir = tuple_list[-1]
    r =[]
    subs = 'Report_'
    r = [i for i in tuple_list if subs in i] 
    print ("List of directory in the Remote dir  : " + str(r)) 
    namedir=sorted(r)[-1]
    print ("picked directory for transfer : " + str(namedir))

    
    logging.debug('Directory is Jacob %s',namedir)

    # Execute find command non recursively in emdba server after ssh login
    logging.info('Getting Report directories under %s ',remote_dir)
    
    dest_dir = tmp_dir
    print("Destination Dir " + tmp_dir)
    sour_dir = remote_dir+namedir 
    print ("Source Dir " + sour_dir)
     
    
    print(sour_dir)
    os.chdir(sour_dir)
    num = 0 
    for file in glob.glob("Report_*"):
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
    	for file in glob.glob("Report_*"):
            shutil.copy(file, dest_dir)
      
    else:
        logging.error('No Report.out files present under %s',sour_dir)
        exit_handler()
    
  # Perform database cleanup
    logging.info('Calling cleanup_emdba_tables()')
    cleanup_emdba_tables()

    # Inserting new data into emdba tables
    logging.info('Calling populate_emdba_tables()')
    populate_emdba_tables()  
     

if __name__ == '__main__':
   remote_fetch_operations()

logging.info('######## LOG END ############\n\n')





