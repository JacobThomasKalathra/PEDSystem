#!/usr/bin/python

'''
    PED flask application
'''
# Import modules
from flask import Flask, render_template, flash, request, url_for, redirect, session, logging    
from passlib.hash import sha256_crypt
from connect_db import OracleDB
from functools import wraps
from flask import jsonify
from datetime import timedelta
import datetime
import collections
import random
import json
import os
import os.path
import re 
import glob
import yaml
import shutil

from string import Template
import logging
import sys

# Create Flask application Object
app = Flask(__name__, instance_relative_config=True)

# Load PED default config dictionary values
app.config.from_object('config')

# Load PED secret config from instance folder
app.config.from_pyfile('config.py')

# Create random  session key
app.config['SECRET_KEY'] = 'd369342136ecd032f8b4a930b6bb2e0e'

# Set session idle timeout
app.permanent_session_lifetime = timedelta(minutes=30)

# On every route call,reactivate session if timeout not met
@app.before_request
def make_session_permanent():
    session.permanent = True

# Login/Registration route 
@app.route('/ped', strict_slashes=False, methods=['GET', 'POST'])
def login():
    # Form submitted using POST
    if request.method == 'POST':
        email = request.form['email']

        # Identify login submit or register submit based on submit value
        button_type = request.form['btn-submit']

        # Create an object of DB Wrapper Class
        db = OracleDB()
		
        # Connect to DB with Autocommit enabled,raise exception if error
        try:
            cur = db.connect()
        except Exception as error:
            flash('Sorry,Error in Database Connection', 'danger')
            return redirect(url_for('login'))

	# Registration form submitted,store encrypted password in database
        if button_type == "register":
            # Use SHA 256 one-way hash function to secure password
            password = sha256_crypt.hash(request.form['regpassword'])

            # Check if any existing record for the user
            cur.execute("select * from INV_USER_LIST where email=:1", (email, ))
            users = cur.fetchall()

       	    # Email already exists in database
            if cur.rowcount > 0:
                db.disconnect()
                flash('Already registered email address', 'danger')
                return redirect(url_for('login'))
            else:
                try:
		    # Insert new user into database
                    cur.execute("INSERT INTO INV_USER_LIST(EMAIL,PASSWD,ENTERED_BY,ENTERED_DTTM,UPDATED_BY,UPDATED_DTTM) VALUES(:1, :2, :3, :4, :5, :6)", (email, password,email,datetime.datetime.now(),email,datetime.datetime.now()))
                    flash('Successfully registered ,Please login now', 'success')
                except:
                    flash('Sorry,Error in registration', 'danger')
                finally:
                    # Disconnect Database
                    db.disconnect()
                    return redirect(url_for('login'))
        else:
	    # Normal login
            password = request.form['password']

            # Retrieve encrypted password and admin status from database
            cur.execute("select PASSWD,IS_ADMIN from INV_USER_LIST where email=:1", (email, ))
            user_details = cur.fetchone()
            db.disconnect()

	    # User not available in database
            if cur.rowcount == 0:
                flash('Sorry,you are not a registered user', 'danger')
                return redirect(url_for('login'))

	   # Valid Email id
            else:
		# Use sha256 verify function to match hashes of current password against one in DB
                if sha256_crypt.verify(password, user_details[0]):

		    # Valid User. Set session variables
                    session['logged_in'] = True
                    session['email'] = email
                    session['username'] = re.split('[. @ _ -]', email)[0].capitalize() 
                    session['is_admin'] = user_details[1]
                    session['db_error'] = 'Sorry,Error in Database Connection'

                    # Read emdba server timezone from emdba config
                    with open(app.config["EMDBA_CONF_FILE"], 'r') as file:
                        conf = yaml.load(file)
                    session['emdba_tz']     = conf["emdba_details"]["time_zone"]


		    # Redirct to application dashboard
                    return redirect(url_for('dashboard'))
                else:
                    flash('Invalid Password', 'danger')
                    return redirect(url_for('login'))
	# Render login/Registration page to user
    return render_template('login.html')

# Flask decorator for authorization

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized access / Session expired, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap


# Dashboard route

@app.route('/dashboard')
@is_logged_in
def dashboard():
      # Create an object of DB Wrapper Class
      db = OracleDB()

      # Connect to DB with Autocommit enabled,raise exception if error
      try:
          cur = db.connect()
      except Exception as error:
          return redirect(url_for('logout',logout_msg=session['db_error']))

      # Get emdba statistics from DB
      cur.execute("SELECT 'Completed' AS STATUS, count(*) from INV_EMDBA_ENV UNION SELECT 'Skipped' AS STATUS, count(*) from INV_EMDBA_SKIP UNION SELECT 'Error' AS STATUS , COUNT(*) FROM INV_EMDBA_ERROR UNION SELECT 'Locked' AS STATUS , COUNT(*) FROM INV_EMDBA_LOCK UNION SELECT 'Blackout' AS STATUS , COUNT(*) FROM INV_EMDBA_BLACKOUT")
      statistics = dict(cur.fetchall())
      # Total DB Servers exclude blackout
      statistics['Total'] = sum(statistics.itervalues()) - statistics['Blackout']

      # Get distinct Oracle versions and count

     #SELECT  ORVER , CNT  FROM (SELECT ORACLE_VERSION AS ORVER, COUNT(*) as cnt FROM INV_EMDBA_ENV GROUP BY ORACLE_VERSION  ) ORDER BY SUBSTR(ORVER,1,2) DESC
      cur.execute("SELECT ORACLE_VERSION, COUNT(*) FROM INV_EMDBA_ENV GROUP BY ORACLE_VERSION")
     # SELECT ORACLE_VERSION, COUNT(*) FROM INV_EMDBA_ENV GROUP BY ORACLE_VERSION
      dbversions = dict(cur.fetchall())
      dbversions = collections.OrderedDict(sorted(dbversions.items()))
      dbversions = collections.OrderedDict(list(dbversions.items())[::-1])
      cur.execute("SELECT 'FSCM' AS STATUS, count(*) from INV_EMDBA_ENV   WHERE Application LIKE 'Financials%' UNION  SELECT 'CRM' AS STATUS, count(*) from INV_EMDBA_ENV   WHERE Application LIKE 'CRM%' UNION  SELECT 'Portal' AS STATUS, count(*) from INV_EMDBA_ENV   WHERE Application LIKE 'Portal Solutions%' UNION SELECT 'ELS' AS STATUS, count(*) from INV_EMDBA_ENV   WHERE Application LIKE 'Enterprise Learning Solutions%' UNION SELECT 'PTools' AS STATUS, count(*) from INV_EMDBA_ENV   WHERE Application LIKE 'PeopleTools%' or Application LIKE 'Enterprise Objects%' UNION SELECT 'HRMS' AS STATUS, count(*) from INV_EMDBA_ENV   WHERE Application LIKE 'HRMS%'  UNION SELECT 'EPM' AS STATUS, count(*) from INV_EMDBA_ENV   WHERE Application LIKE 'EPM%' UNION SELECT 'CS' AS STATUS, count(*) from INV_EMDBA_ENV   WHERE Application LIKE  'Campus Solutions%'")

      #cur.execute("SELECT 'FSCM' AS STATUS, count(*) from INV_EMDBA_ENV   WHERE Application LIKE 'Financials%' UNION  SELECT 'CRM' AS STATUS, count(*) from INV_EMDBA_ENV   WHERE Application LIKE 'CRM%' UNION  SELECT 'Portal' AS STATUS, count(*) from INV_EMDBA_ENV   WHERE Application LIKE 'Portal Solutions%' UNION SELECT 'ELS' AS STATUS, count(*) from INV_EMDBA_ENV   WHERE Application LIKE 'Enterprise Learning Solutions%' UNION SELECT 'PTools' AS STATUS, count(*) from INV_EMDBA_ENV   WHERE Application LIKE 'PeopleTools%' or Application LIKE 'Enterprise Objects%' UNION SELECT 'HRMS and CS' AS STATUS, count(*) from INV_EMDBA_ENV   WHERE Application LIKE 'HRMS%' or Application LIKE 'Campus Solutions%' UNION SELECT 'EPM' AS STATUS, count(*) from INV_EMDBA_ENV   WHERE Application LIKE 'EPM%'")
      application = dict(cur.fetchall())
      
      logging.info('######## In dashboard ############\n')
      values = application.values()
      mkeys = application.keys()
      values_list = list(values)
      mkey_list = list(mkeys)
      session['mvalues'] = values_list
      session['mmkey'] = mkey_list
      session['mApps-detail'] = str(application)
      #print("detail  /  " + str(application))
      #print(values_list)
      #print(mkey_list)

      cur.execute("SELECT dbtype, count(*) FROM (SELECT (CASE DB_TYPE WHEN '1' THEN 'USERP' WHEN '2' THEN 'BASS2P' WHEN '3' THEN 'USERD' WHEN '4' THEN 'BASS2D' WHEN '5' THEN 'NONDEP' END) AS dbtype FROM INV_EMDBA_ENV) GROUP BY dbtype")
      db_type = dict(cur.fetchall())
      #print("db_type-detail  " + str(db_type))
      session['db_type-detail'] = str(db_type)
      mdb_type=db_type.values()
      db_list = list(mdb_type)
      
      mdb_list=db_list[::-1]
      session['mvalues1'] = mdb_list
      #print(mdb_list)

 
      # Get timestamp of report generated
      cur.execute("SELECT DISTINCT(REP_TIMESTAMP) FROM INV_EMDBA_ENV")
      try:
          session['report_time'] = cur.fetchone()[0]
      except:
          session['report_time'] = ''
      db.disconnect()

      return render_template('dashboard.html',statistics=statistics,dbversions=dbversions, db_type=db_type)

  



# DB Info route

@app.route('/db_info' , methods=['GET', 'POST'])

@is_logged_in
def db_info():
      db = OracleDB()

      # Connect to DB with Autocommit enabled,raise exception if error
      try:
          cur = db.connect()
      except Exception as error:
          return redirect(url_for('logout',logout_msg=session['db_error']))
          
      if request.method == 'POST':
           button_type = request.form['submit']
           dbtype = request.form.get('editedText')
           req = request.form
       	   #print(dbtype)
           
       	   return redirect(request.url) 

      # Get DB info 
      cur.execute("SELECT  /*+ FIRST_ROWS(10) */  DBSERVER,CASE DB_TYPE WHEN '1' THEN 'USERP' WHEN '2' THEN 'BASS2P' WHEN '3' THEN 'USERD' WHEN '4' THEN 'BASS2D' WHEN '5' THEN 'NONDEP' END ,DBNAME,SLOT,DBOWNER,ORACLE_VERSION,DB_CREATION_DT,LAST_ACCESS_DATE,CEIL(sysdate - (to_date(LAST_ACCESS_DATE, 'YYYY-MM-DD'))-1)  AS \"DAYS NOT ACCESSED FOR\",APPLICATION,TOOLS_MAJ_VERSION,TOOL_PTCH_VERSION,PATCH,DB_CHAR  from INV_EMDBA_ENV WHERE last_access_date <>'NA'  union SELECT /*+ FIRST_ROWS(10) */  DBSERVER,CASE DB_TYPE WHEN '1' THEN 'USERP' WHEN '2' THEN 'BASS2P' WHEN '3' THEN 'USERD' WHEN '4' THEN 'BASS2D' WHEN '5' THEN 'NONDEP' END ,DBNAME,SLOT,DBOWNER,ORACLE_VERSION,DB_CREATION_DT,LAST_ACCESS_DATE, -1  AS \"DAYS NOT ACCESSED FOR\" ,APPLICATION,TOOLS_MAJ_VERSION,TOOL_PTCH_VERSION,PATCH,DB_CHAR  from INV_EMDBA_ENV WHERE last_access_date ='NA'")

      #cur.execute("SELECT  /*+ FIRST_ROWS(10) */  DBSERVER,CASE DB_TYPE WHEN '1' THEN 'USER:PROD' WHEN '2' THEN 'BASS2:PROD' WHEN '3' THEN 'USER:DEV' WHEN '4' THEN 'BASS2:DEV' WHEN '5' THEN 'Non-Dep' END ,DBNAME,SLOT,DBOWNER,ORACLE_VERSION,DB_CREATION_DT,LAST_ACCESS_DATE,CEIL(sysdate - (to_date(LAST_ACCESS_DATE, 'YYYY-MM-DD'))-1)  AS \"DAYS NOT ACCESSED FOR\",APPLICATION,TOOLS_MAJ_VERSION,TOOL_PTCH_VERSION,PATCH,DB_CHAR  from INV_EMDBA_ENV WHERE last_access_date <>'NA'  union SELECT /*+ FIRST_ROWS(10) */  DBSERVER,CASE DB_TYPE WHEN '1' THEN 'USER:PROD' WHEN '2' THEN 'BASS2:PROD' WHEN '3' THEN 'USER:DEV' WHEN '4' THEN 'BASS2:DEV' WHEN '5' THEN 'Non-Dep' END ,DBNAME,SLOT,DBOWNER,ORACLE_VERSION,DB_CREATION_DT,LAST_ACCESS_DATE, -1  AS \"DAYS NOT ACCESSED FOR\" ,APPLICATION,TOOLS_MAJ_VERSION,TOOL_PTCH_VERSION,PATCH,DB_CHAR  from INV_EMDBA_ENV WHERE last_access_date ='NA'")
      #cur.execute(query)
      db_info = cur.fetchall()

      db.disconnect()

      return render_template('db_info.html',db_info=db_info)




@app.route('/server_info')
@is_logged_in
def server_info():
      # Create an object of DB Wrapper Class
      db = OracleDB()

      # Connect to DB with Autocommit enabled,raise exception if error
      try:
          cur = db.connect()
      except Exception as error:
          return redirect(url_for('logout',logout_msg=session['db_error']))

      # Get server info 
     # cur.execute("SELECT /*+ FIRST_ROWS(10) */ HOST_NAME1, UPTIME1, SYSLOAD1 ,VM_R,VM_B,VM_WA,VM_SWPD,IOSTAT,DEFUNCT,DBSTAT_ALL,DBSTAT_UP,DBSTAT_DOWN,DBSTAT_SKIP , TO_TIMESTAMP( LASTUPDATE , 'HH24:MI:SS-DD-MM-YYYY') AS \"TIMESTAMP\" from  PED_SERVER_DETAIL   where LASTUPDATE is not    null")
      cur.execute("SELECT /*+ FIRST_ROWS(10) */ HOST_NAME1, UPTIME1, SYSLOAD1 ,VM_R,VM_B,VM_WA,VM_SWPD,IOSTAT,DEFUNCT,DBSTAT_ALL,DBSTAT_UP,DBSTAT_DOWN,DBSTAT_SKIP , TO_TIMESTAMP( LASTUPDATE , 'HH24:MI:SS-DD-MM-YYYY') AS \"TIMESTAMP\" from  PED_SERVER_DETAIL   where to_date(SUBSTR(LASTUPDATE, 10, 10) ,'DD-MM-YYYY') in (Select max(to_date(SUBSTR(LASTUPDATE, 10, 10) ,'DD-MM-YYYY')) from PED_SERVER_DETAIL) ")

      server_info = cur.fetchall()

      db.disconnect()

      return render_template('server_info.html',server_info=server_info)




# Route for Tools Version

@app.route('/tools_version')
@is_logged_in
def tools_version():
      # Create an object of DB Wrapper Class
      db = OracleDB()

      # Connect to DB with Autocommit enabled,raise exception if error
      try:
          cur = db.connect()
      except Exception as error:
          return redirect(url_for('logout',logout_msg=session['db_error']))

      # Get  PT Tools Version
      cur.execute("SELECT TOOLS_MAJ_VERSION, COUNT(*) FROM INV_EMDBA_ENV GROUP BY TOOLS_MAJ_VERSION")
      tools_info = cur.fetchall()

      db.disconnect()

      return render_template('tools_version.html',tools_info=tools_info)

# Route for DB Version Count

@app.route('/db_version_count')
@is_logged_in
def db_version_count():
      # Create an object of DB Wrapper Class
      db = OracleDB()

      # Connect to DB with Autocommit enabled,raise exception if error
      try:
          cur = db.connect()
      except Exception as error:
          return redirect(url_for('logout',logout_msg=session['db_error']))

      # Get Oracle Version Info 
      cur.execute("SELECT ORACLE_VERSION, COUNT(*) FROM INV_EMDBA_ENV GROUP BY ORACLE_VERSION")
      oracle_versions = cur.fetchall()

      db.disconnect()

      return render_template('db_version_count.html',oracle_versions=oracle_versions)

# Route for DB status

@app.route('/db_error')
@is_logged_in
def db_error():
      # Create an object of DB Wrapper Class
      db = OracleDB()

      # Connect to DB with Autocommit enabled,raise exception if error
      try:
          cur = db.connect()
      except Exception as error:
          return redirect(url_for('logout',logout_msg=session['db_error']))

      cur.execute("select 'ERROR' as TABLE_NAME,DBSERVER ,SLOT, DBNAME ,  REP_TIMESTAMP as TIMESTAMP FROM INV_EMDBA_ERROR ")
      db_test_cnt = cur.fetchall()

      db.disconnect()

      return render_template('db_test.html',db_test_cnt=db_test_cnt)

@app.route('/db_skip')
@is_logged_in
def db_skip():
      # Create an object of DB Wrapper Class
      db = OracleDB()

      # Connect to DB with Autocommit enabled,raise exception if error
      try:
          cur = db.connect()
      except Exception as error:
          return redirect(url_for('logout',logout_msg=session['db_error']))

      cur.execute("select 'SKIP' as TABLE_NAME,DBSERVER , SLOT ,'NODB' as DBNAME , REP_TIMESTAMP as TIMESTAMP FROM INV_EMDBA_SKIP ")
      db_test_cnt = cur.fetchall()

      db.disconnect()

      return render_template('db_test.html',db_test_cnt=db_test_cnt)
@app.route('/db_Lock')
@is_logged_in
def db_Lock():
      # Create an object of DB Wrapper Class
      db = OracleDB()

      # Connect to DB with Autocommit enabled,raise exception if error
      try:
          cur = db.connect()
      except Exception as error:
          return redirect(url_for('logout',logout_msg=session['db_error']))

      cur.execute("select 'LOCK' as TABLE_NAME, DBSERVER , SLOT ,'NODB' as DBNAME , REP_TIMESTAMP as TIMESTAMP FROM INV_EMDBA_LOCK ")
      db_test_cnt = cur.fetchall()

      db.disconnect()

      return render_template('db_test.html',db_test_cnt=db_test_cnt)
@app.route('/db_test')
@is_logged_in
def db_test():
      # Create an object of DB Wrapper Class
      db = OracleDB()

      # Connect to DB with Autocommit enabled,raise exception if error
      try:
          cur = db.connect()
      except Exception as error:
          return redirect(url_for('logout',logout_msg=session['db_error']))

      cur.execute("select 'BLACKOUT' as TABLE_NAME,DBSERVER , 'NOSLOT' as SLOT   ,'NODB' as DBNAME , REP_TIMESTAMP as TIMESTAMP FROM INV_EMDBA_BLACKOUT")
      db_test_cnt = cur.fetchall()

      db.disconnect()

      return render_template('db_test.html',db_test_cnt=db_test_cnt)








# Route for Patch Count

@app.route('/ora_patch_count')
@is_logged_in
def ora_patch_count():
      # Create an object of DB Wrapper Class
      db = OracleDB()

      # Connect to DB with Autocommit enabled,raise exception if error
      try:
          cur = db.connect()
      except Exception as error:
          return redirect(url_for('logout',logout_msg=session['db_error']))

      # Get DB Patch Info 
      cur.execute("select oracle_version, patch ,count(*),(select count(*) from inv_emdba_env i where i.oracle_version=o.oracle_version group by oracle_version  ) from inv_emdba_env o group by oracle_version, patch order by oracle_version")
      patch_tuple = cur.fetchall()

      # Using an ordered data structure like list of tuples.
      # This is to avoid table rendering difficulties using datatables over nested dictionary
      ora_matched=[]
      patch_versions=[]
      for ora_version,patch,patch_count,ora_count in patch_tuple:
        if ora_version not in ora_matched:
          ora_matched.append(ora_version) 
          # Skipping oracle version count
          patch_versions.append((ora_version,''))
          patch_versions.append((patch,patch_count))
        else: 
          patch_versions.append((patch,patch_count))

      db.disconnect()
      return render_template('ora_patch_count.html',patch_versions=patch_versions)

# Update emdba configuration yml file

@app.route('/update_emdba_config',methods=['GET', 'POST'])
@is_logged_in
def update_emdba_config():

    emdba_dict = {}
    emdba_conf = app.config["EMDBA_CONF_FILE"]

    # Form submitted
    if request.method == 'POST':
        emdba_dict['host'] = request.form['host']
        emdba_dict['username'] = request.form['username']
        emdba_dict['password'] = request.form['password']
        emdba_dict['remote_dir'] = request.form['remote_dir']
        emdba_dict['time_zone'] = request.form['time_zone']

        # If all fields are blank
        if all(value == '' for value in emdba_dict.values()):
            msg = 'Please update atleast one field'
            return render_template('update_emdba_config.html',msg=msg)

        # Load file using yml parser. Exception if error
        try:
            with open(emdba_conf, 'r') as file:
                conf = yaml.load(file)
        except Exception as error:
          msg = 'Sorry,could not open emdba configuration file'
          return render_template('update_emdba_config.html',msg=msg)

        # Form submitted fields contain unicode by default.Ignore them using ascii encoding
        for key,value in emdba_dict.items():
            if value:
                conf['emdba_details'][key] = value.encode('ascii', 'ignore')

        # Open yml in write mode.Dump updated fields along with others
        try:
            with open(emdba_conf, 'w') as file:
                file.write( yaml.dump(conf, default_flow_style=False))
            msg = 'File updated successfully'
        except Exception as error:
            msg = 'Sorry,could not update emdba configuration file'
        finally:
            return render_template('update_emdba_config.html',msg=msg)

    return render_template('update_emdba_config.html')

# Update emdba configuration yml file

# Server Management 



@app.route('/server_monitoring',methods=['GET', 'POST'])
@is_logged_in
def server_monitoring():
   os.chdir(r"/var/www/FlaskApp/FlaskApp/ServerMon")
   
   #os.system("/var/cust_emdba/sever_monitor.sh &")
   os.system("/var/www/FlaskApp/FlaskApp/ServerMon/sever_monitor.sh &")
   if os.path.exists('/var/www/FlaskApp/FlaskApp/ServerMon/chkServers/chkServersBasicStatus'):
      db = OracleDB()
      try:
         cur = db.connect()
      except Exception as error:
          return redirect(url_for('logout',logout_msg=session['db_error'])) 
   else :
         return redirect(url_for('logout',logout_msg=session['db_error']))
   path = '/apps_autofs/recovery/ENTERPRISE/opsdba/emdba/sharedLogs/chkServers'
   dest = '/var/www/FlaskApp/FlaskApp/ServerMon/chkServers'
   if os.path.exists(dest):
      shutil.rmtree(dest)
   destination= shutil.copytree(path, dest)
   #print("After copying file:")
   #print(os.listdir(dest))
   files = os.listdir (dest)

   def get_log(logfile):
     pathfile= logfile +".Error" 
     os.system("cat " +pathfile+" > merged.txt")
     f = open("merged.txt", "r")
     text1 = f.read()
     f.close() 
     res = text1
     return res
   
   def FileCheck(fn):
    try:
      file = open(fn, "r")
      content = file.read()
      val=int(content.strip())
      return val
    except IOError:
      #print "Error: File does not appear to exist."
      return 0
   PATH='/var/www/FlaskApp/FlaskApp/ServerMon/chkServers/chkServersBasicStatus'

   if os.path.isfile(PATH) and os.access(PATH, os.R_OK):
    #print "File exists and is readable/there"
    file = open('/var/www/FlaskApp/FlaskApp/ServerMon/chkServers/chkServersBasicStatus')
    merror = FileCheck('/var/www/FlaskApp/FlaskApp/ServerMon/chkServers/same_error_count')
    session['merr'] = merror
    for line in file.readlines():
       #print line
       strip_lines=line.strip()
       listli=strip_lines.split()
       #print(listli)
       mycontent = listli[0]
       #print ('value is ' ,mycontent)
       session['status'] = mycontent
       if mycontent == "SUCCESS":
         status = "SUCCESS"
         session['mStatus'] =1
         os.system("cat /var/www/FlaskApp/FlaskApp/ServerMon/chkServers/chkServersBasic_*.success > merged.html")
         f = open("merged.html", "r")
	 text = f.read()
	 #print text
         f.close()
         successFile =[]
         successFile = glob.glob("/var/www/FlaskApp/FlaskApp/ServerMon/chkServers/chkServersBasic_*.success")
         #print (type(successFile))
        
         NameofFile=  successFile[0]
         NameofFile = NameofFile[48:79:]
         session['mNameofFile'] =NameofFile
         #print (NameofFile)

	 session['mval_list'] = text
         Timeoffile = NameofFile[16::]
         #print (Timeoffile)

         report_time = re.sub('-','', Timeoffile )
	 report_time = datetime.datetime.strptime(report_time, '%Y%m%d%H%M%S').strftime('%d/%m/%Y %H:%M:%S')
         #print (report_time)
         session['mtime'] =report_time
         
         Logfile = os.system("ls  /var/www/FlaskApp/FlaskApp/ServerMon/chkServers/summary/*.Error | sed -e 's/\..*$//' > Logfile.txt")
         #Logfilecnt = os.system("ls /tmp/chkServers/*.Error | sed -e 's/\..*$//' |wc -l")
         
         
         with open('Logfile.txt') as f:
              line = f.readline()
              result = {}
              
              while line:
                  line = f.readline()
                  line = line.rstrip()
                  
                  if line[72:87:] != '':
                     result[line[72:87:]]= ''

         #print(result.values())
         #print(result.keys())
         print(len(result.keys()))
         session['mlenglst'] =  len(result.keys())
         #print("Data type  : ", type(Logfilecnt))
         #cur.execute("select ERR_DATE,ERR_COUNT,LOG_CONTENT from PSFT_ERRORFILE_LOG ")
         cur.execute("select substr(err_date,1,4) ||'-'|| substr(err_date,5,2) ||'-'|| substr(err_date,7,2) ||' '|| substr(err_date,10,2)  ||':'||  substr(err_date,12,2) ||':'||  substr(err_date,14,2) as err,ERR_COUNT,LOG_CONTENT from PSFT_ERRORFILE_LOG ")
     
         result = cur.fetchall()         
         db.disconnect()
         if len(result) > 0:
           session['mresult'] = result
           #od = collections.OrderedDict(reversed(sorted(result.items())))
           od = result 
         else :
           session['mresult'] = {'No ErrorFile': ''}

           od ={'No ErrorFile': ''}

         #od = collections.OrderedDict(reversed(sorted(result.items())))
         #od =result.items()

         #print(od.keys())
       elif mycontent == "NEW_ERROR" or mycontent == "SAME_ERROR" :
         status = mycontent
         if mycontent == "NEW_ERROR" :
            session['mStatus'] =2
         else :
            session['mStatus'] =3
         os.system("cat /var/www/FlaskApp/FlaskApp/ServerMon/chkServers/chkServersBasic_*.error > merged.html")
         f = open("merged.html", "r")
	 text = f.read()
	 #print text
         f.close()
         successFile =[]
         successFile = glob.glob("/var/www/FlaskApp/FlaskApp/ServerMon/chkServers/chkServersBasic_*.Error")
         #print (successFile)
       
         NameofFile=  successFile[0]
         NameofFile = NameofFile[48:79:]
         session['mNameofFile'] =NameofFile

         session['mval_list'] = text
         
         Timeoffile = NameofFile[16::]
         
         report_time = re.sub('-','', Timeoffile )
	 report_time = datetime.datetime.strptime(report_time, '%Y%m%d%H%M%S').strftime('%d/%m/%Y %H:%M:%S')
         #print (report_time)
         session['mtime'] =report_time
         
         Logfile = os.system("ls  /var/www/FlaskApp/FlaskApp/ServerMon/chkServers/summary/*.Error | sed -e 's/\..*$//' > Logfile.txt")
              
         
         with open('Logfile.txt') as f:
              line = f.readline()
              result = {}
              
              while line:
                  line = f.readline()
                  line = line.rstrip()
                  
                  if line[72:87:] != '':
                     result[line[72:87:]]= ''
         #print(result.values())
         #print(result.keys())
         print(len(result.keys()))
         session['mlenglst'] =  len(result.keys())
         #print("Data type  : ", type(Logfilecnt))
         #cur.execute("select ERR_DATE,ERR_COUNT,LOG_CONTENT from PSFT_ERRORFILE_LOG ")
         cur.execute("select substr(err_date,1,4) ||'-'|| substr(err_date,5,2) ||'-'|| substr(err_date,7,2) ||' '|| substr(err_date,10,2)  ||':'||  substr(err_date,12,2) ||':'||  substr(err_date,14,2) as err,ERR_COUNT,LOG_CONTENT from PSFT_ERRORFILE_LOG ")
     
         result = cur.fetchall()         
         db.disconnect()

         if len(result) >0:
           session['mresult'] = result
           #od = collections.OrderedDict(reversed(sorted(result.items())))
           od = result
         else :
           session['mresult'] = {'No ErrorFile': ''}

           od ={'No ErrorFile': ''}
         

       else:
        status =""
        session['mval_list'] = 'No Log File Available'

        od ={'No ErrorFile': ''}
        session['mStatus'] =status
        session['mresult'] = {}
       


       #print ("Status is ", status)
    file.close()
   else:
    print ("Not their")
   

    
   return render_template('server_monitoring.html',od=od);


# User Management for Admin

@app.route('/user_mangement',  methods=['GET', 'POST'])
@is_logged_in
def user_management():

    # Create an object of DB Wrapper Class
    db = OracleDB()

    # Connect to DB with Autocommit enabled,raise exception if error
    try:
        cur = db.connect()
    except Exception as error:
        flash('Sorry,Error in Database Connection', 'danger')
        return redirect(url_for('login'))
    # Render html with list of current users excluding logged in user
    cur.execute("select EMAIL from INV_USER_LIST WHERE EMAIL NOT IN ('" + session['email'] + "') order by EMAIL")
    user_list = cur.fetchall()

    # Form submitted using POST
    if request.method == 'POST':
        button_type = request.form['submit']

        #If submission from Add User page
        if button_type == "add_user":
            user_add_email = request.form['user_add_email']
            is_admin =  "Y" if request.form.get('isadmin') else "N"

            # Check admin type if user exists
            cur.execute("select IS_ADMIN from INV_USER_LIST where email=:1", (user_add_email, ))
            admin_type = cur.fetchone()

            # New user
            if cur.rowcount == 0:
                cur.execute("INSERT INTO INV_USER_LIST(EMAIL,PASSWD,ENTERED_BY,ENTERED_DTTM,UPDATED_BY,UPDATED_DTTM,IS_ADMIN) VALUES(:1, :2, :3, :4, :5, :6, :7)", (user_add_email, sha256_crypt.hash("ped123"),session['email'],datetime.datetime.now(),session['email'],datetime.datetime.now(),is_admin))
                msg = "User added successfully"

            else:
                # Email already exists in database with same ACL
                if is_admin == admin_type[0]:
                    msg = "User already exists"
                # Admin Request for normal user
                else:
                    if is_admin == 'Y':
                        cur.execute("UPDATE INV_USER_LIST SET IS_ADMIN = :1,UPDATED_BY = :2,UPDATED_DTTM = :3 WHERE EMAIL = :4", (is_admin,session['email'],datetime.datetime.now(),user_add_email))
                        msg = "Admin access granted for "+user_add_email
                    else:
                        msg = "User already exists"
        # If Submission happened from Remove User Page
        elif button_type == "remove_user":

            # Identify remove user / revoke admin form is submitted
            form_type = request.form['optradio']

            # Get selected user email for remove/revoke
            user_remove_email     = request.form['ddlListName']

            # Remove user from DB
            if form_type == 'remove_form':
                cur.execute("DELETE FROM INV_USER_LIST WHERE EMAIL = :1", (user_remove_email,))
                msg = "Successfully removed "+ user_remove_email

            # Revoke admin access for user
            elif form_type == 'revoke_form':
                cur.execute("UPDATE INV_USER_LIST SET IS_ADMIN = 'N',UPDATED_BY = :1,UPDATED_DTTM = :2 WHERE EMAIL = :3", (session['email'],datetime.datetime.now(),user_remove_email))
                msg = "Successfully revoked admin access for "+ user_remove_email
        
        # Update new list of users after addition/deletion
        cur.execute("select EMAIL from INV_USER_LIST")
        user_list = cur.fetchall()

        db.disconnect()
        return render_template('user_management.html',user_list=user_list,msg=msg)

    return render_template('user_management.html',user_list=user_list);

# Fetch  all users/admins based on 'remove user' or 'revoke admin' operation
@app.route('/fetch_users/<operation>')
@is_logged_in
def fetch_users(operation):

      # Create an object of DB Wrapper Class
      db = OracleDB()

      # Connect to DB with Autocommit enabled,raise exception if error
      try:
          cur = db.connect()
      except Exception as error:
          flash('Sorry,Error in Database Connection', 'danger')
          return redirect(url_for('login'))

      # If revoke admin operation, select users from DB where is_admin ='Y'. Else, select both Y & N
      admin_flag = ['Y'] if operation == 'revoke' else ['Y','N']

      # Convert list to string
      admin_flag = "('{0}')".format("','".join(map(str, admin_flag)))

      # Update user list excluding logged in user
      cur.execute("select EMAIL from INV_USER_LIST WHERE IS_ADMIN IN " + admin_flag + " AND EMAIL NOT IN ('" + session['email'] + "') order by EMAIL")
      user_list = cur.fetchall()

      db.disconnect()

      # jsonify results
      return  json.dumps(user_list)

# Session logout

@app.route('/logout')
@app.route('/logout/<logout_msg>')
@is_logged_in
def logout(logout_msg=None):

    # Clear all session variables
    session.clear()
    if logout_msg:
        flash(logout_msg, 'danger')
    else:
        flash('Logged out successfully', 'success')
    return redirect(url_for('login'))



#Enable below lines for development mode
#if __name__ == "__main__":
#    app.run(host='0.0.0.0', port=5001, debug=True)
