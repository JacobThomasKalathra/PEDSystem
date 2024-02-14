'''
    Class for Oracle DB connection and disconnection
    DB Connection parameters read from inv_db_conf.yml file
'''
import cx_Oracle
import yaml
import os 

class OracleDB:
    
    # Constructor
    def __init__(self):
       
        # Read DB Configuration parameters file
        with open(os.path.join(os.path.dirname(__file__),'../conf/emdba_conf.yml'), 'r') as file:
             conf = yaml.load(file)
        self.user     = conf["database_details"]["username"]
        self.server   = conf["database_details"]["host"]
        self.sid      = conf["database_details"]["sid"]
        self.port     = conf["database_details"]["port"]
        self.password = conf["database_details"]["password"]
        # Create Data Source Name
        self.tns      = cx_Oracle.makedsn(self.server, self.port, self.sid)
        self.connection =  None
        self.cursor     =  None 
     
    # DB connection function
    def connect(self):
        self.connection = cx_Oracle.connect(self.user, self.password, self.tns)
		#Enable execution with commit for non-select queries
        self.connection.autocommit = True
        self.cursor = self.connection.cursor()
        return self.cursor

    # DB disconnection function
    def disconnect(self):
        self.cursor.close()
        self.connection.close()
