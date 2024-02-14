import cx_Oracle
dsnStr = cx_Oracle.makedsn("slc04wva.us.oracle.com", "1521", "pmsdevdb")
con = cx_Oracle.connect(user="emdbo",password="ru55",dsn=dsnStr)
cur = con.cursor()
print con.version
cur.execute('select * from INV_USER_LIST')
for result in cur:
    print result
con.close()

