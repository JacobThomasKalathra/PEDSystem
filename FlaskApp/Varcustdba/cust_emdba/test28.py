import cx_Oracle

con = cx_Oracle.connect('emdbo', 'ru55', 'slc04wva.us.oracle.com:/pmsdevdb:pooled',
             cclass = "PMSDEVDB", purity = cx_Oracle.ATTR_PURITY_SELF)

print con.version

con.close()
