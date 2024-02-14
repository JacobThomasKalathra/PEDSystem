import os

# path
path = '/tmp/chkServers'

try:
	os.mkdir(path)
except OSError as error:
	print(error)	

