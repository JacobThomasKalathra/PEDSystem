'''
    Class for Oracle DB connection and disconnection
    DB Connection parameters read from config.py file
'''
import cx_Oracle
import os
from flask import current_app as app

class OracleDB:
    
    # Constructor
    def __init__(self):
        # Read DB Configuration parametersfrom config.py 
        self.user     = app.config["DB_USERNAME"]
        self.server   = app.config["DB_HOST"]
        self.sid      = app.config["DB_SID"]
        self.port     = app.config["DB_PORT"]
        self.password = app.config["DB_PASSWORD"]

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
