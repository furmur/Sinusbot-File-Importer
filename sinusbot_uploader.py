#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import sys
import os
import httplib
import os.path
import getopt

from mutagen.easyid3 import EasyID3

class Sinusbot:
	jwt_token = '' 		#Auth Token
	botId = ''			#Bot ID required for the Login
	url = ''			#Base URL 
	port = 8087 		#default Sinusbot Port
	ssl = False #		Disable SSL by default
	username = ''
	password = ''
	success_count = 0
	error_count = 0
	extensions=['mp3', 'mp4', 'wav', '3gp','flac']
	ignore_dirs=['Scans','covers','Cover','covers_ver.1','covers_ver.2']
	json_files_list = None

	def __init__(self, url, port, username, password, ssl):
		self.url = url
		self.port = port
		self.ssl = ssl
		self.username = username
		self.password = password
		self.botId = self.DefaultId()
		self.success_count = 0
		self.error_count = 0

	def DefaultId(self):
		c = httplib.HTTPSConnection(self.url, self.port) if self.ssl else httplib.HTTPConnection(self.url, self.port)

		c.request("GET", "/api/v1/botId")
		response = c.getresponse()

		if response.status == 200:
			j = json.loads(response.read())
			c.close()
			return j['defaultBotId']
		else:
			c.close()
			return ''

	def Auth(self):
		c = httplib.HTTPSConnection(self.url, self.port) if self.ssl else httplib.HTTPConnection(self.url, self.port)

		data =  {"username":self.username, "password":self.password, "botId": str(self.botId)}  #Parse the botId with str() to pre event a golang error in case of unicode
		hdr = {"Content-type": "application/json"}

		c.request("POST", "/api/v1/bot/login", json.dumps(data), hdr)
		response = c.getresponse()

		if response.status == 200:
			response = str(response.read())
			j = json.loads(response)
			
			try:
					self.jwt_token = j['token']
					c.close()
					self.username = ''
					self.password = '' 
					return True
					
				
			except:	
					c.close()
					print 'Could not get token: %s' % (response)
					return False
			
		
		else:
			c.close()
			return False
			
	def Upload(self, LocalPath, destination_folder_uuid = None):
	
		if not os.path.isfile(LocalPath):
			return False

		try:
			f = open(LocalPath, 'r')
			bytes = f.read()
			f.close()
		except: 
			print 'Could not read -> ' + LocalPath
			return False

		c = httplib.HTTPSConnection(self.url, self.port) if self.ssl else httplib.HTTPConnection(self.url, self.port)

		hdr = {"Content-type": "application/octet-stream", "Authorization": "bearer " + str(self.jwt_token), "Content-Length": len(bytes)}

		if destination_folder_uuid:
			query = "/api/v1/bot/upload?folder=%s" % unicode(destination_folder_uuid)
			c.request("POST", str(query), bytes, hdr)
		else:
			c.request("POST", "/api/v1/bot/upload", bytes, hdr)

		response = c.getresponse()

		if response.status == 200:
			c.close()
			self.success_count += 1
			return True
		else:
			print "got status : " + str(response.status)
			print "body: " + str(response.read())
			c.close()
			self.error_count += 1
			return False

	def checkFile(self,name, folder_uuid):

		#name = unicode(name, "utf-8")
		#print "checkFile('%s',%s)" % (name,folder_uuid)

		if not self.json_files_list:
			hdr = {"Content-type": "application/json", "Authorization": "bearer " + str(self.jwt_token) }
			c = httplib.HTTPSConnection(self.url, self.port) if self.ssl else httplib.HTTPConnection(self.url, self.port)

			c.request("GET", "/api/v1/bot/files", None, hdr)
			r = c.getresponse()
			if r.status != 200:
				raise Exception('failed to load files list')
			r = str(r.read())

			self.json_files_list = json.loads(r)

		#print self.json_files_list

		jf = filter(lambda f: "title" in f and f["title"]==name and f["parent"]==folder_uuid, self.json_files_list)
		if jf:
			uuid = jf[0]['uuid']
			#print "file '%s' exists with uuid %s" % (name, uuid)
			return True
		return False

	def ensureFolder(self, name, parent_folder_uuid = ""):
		data = { "name": name, "parent": parent_folder_uuid }

		if parent_folder_uuid is None:
			parent_folder_uuid = ""

		name = unicode(name, "utf-8")
		#print "ensureFolder('%s',%s)" % (name,parent_folder_uuid)

		hdr = {"Content-type": "application/json", "Authorization": "bearer " + str(self.jwt_token) }
		c = httplib.HTTPSConnection(self.url, self.port) if self.ssl else httplib.HTTPConnection(self.url, self.port)

		c.request("GET", "/api/v1/bot/files", None, hdr)
		r = c.getresponse()
		if r.status != 200:
			print "ERROR: failed to list directory" + parent_folder_uuid
			return None
		r = str(r.read())

		j = json.loads(r)

		if parent_folder_uuid and not filter(lambda f: f['uuid']==parent_folder_uuid,j):
			print "parent folder with uuid %s doesn't exist. skip processing" % (parent_folder_uuid)
			return None

		jf = filter(lambda f: f["type"]=="folder" and f["title"]==name and f["parent"]==parent_folder_uuid, j)
		if jf:
			uuid = jf[0]['uuid']
			#print "folder '%s' exists. return uuid %s" % (name, uuid)
			return uuid

		c.request("POST", "/api/v1/bot/folders", json.dumps(data), hdr)
		r = c.getresponse()
		if r.status != 201:
			return None

		r = str(r.read())
		c.close()

		j = json.loads(r)

		if j["success"]==False:
			print "ERROR: failed to create folder"
			return None

		uuid = j["uuid"]
		print "created folder '%s' with name %s" % (uuid,name)
		return uuid

def uploadHelper(directory, bot, recurse, parent_uuid = None):
	truePath = os.path.abspath(directory)
	contents = os.listdir(truePath)

	d = os.path.basename(directory)
	if d in bot.ignore_dirs:
		return

	uuid = bot.ensureFolder(d,parent_uuid)
	if not uuid:
		print "ERROR: failed to ensure folder '%s'" % d
		return

	for entry in contents:
		entryTruePath = os.path.join(truePath, entry)
		if os.path.isfile(entryTruePath):
			fileExtension = entryTruePath.split('.')[-1]

			if (fileExtension not in bot.extensions):
				#~ print 'File type not supported: ' + entryTruePath
				continue

			if fileExtension=='mp3':
				mp3_tags = EasyID3(entryTruePath)
				mp3_title = mp3_tags['title'][0]
				if bot.checkFile(mp3_title,uuid):
					#print 'skip existent file: ' + entryTruePath
					continue

			if bot.Upload(entryTruePath,uuid):
				print 'Success uploaded: ' + entryTruePath
			else:
				print 'Error while uploading: ' + entryTruePath

		elif os.path.isdir(entryTruePath) and recurse:
			uploadHelper(entryTruePath, bot, recurse, uuid)

def usage():
	print 'usage: %s [ -h hostname ] [ -p port] [ -U user ] [ -P password ] [ -b remote_dir_uuid ] [ -r ] [ -s ] LOCAL_DIRECTORY' % sys.argv[0]
	print '''
  args:
    LOCAL_DIRECTORY    directory to upload

  options:
    -h, --host         API hostname (default: 127.0.0.1)
    -p, --port         API port (default: 8087)
    -U, --user         auth username (default: sinus)
    -P, --password     auth password (default: sinus)
    -r, --recursive    process directory recursively
    -s, --ssl          enable SSL (disabled by default)
    -b, --base         specify remote base directory uuid (default: empty for the root)
    '''

if __name__ == "__main__":

	host = '127.0.0.1'
	port = '8087'
	username = 'sinus'
	password = 'sinus'
	ssl_enabled = False
	recursive = False
	base_folder_uuid = None

	try:
		opts, args = getopt.getopt(
			sys.argv[1:],
			"h:p:U:P:b:rs",
			["host=","port=","user=","password=","=base","recursive","ssl"]
		)
		for o, a in opts:
			if o in ('-h','--host'):
				host = a
			elif o in ('-p','--port'):
				port = a
			elif o in ('-U','--user'):
				username = a
			elif o in ('-P','--password'):
				password = a 
			elif o in ('-b','--base'):
				base_folder_uuid = a
			elif o in ('-r','--recursive'):
				recursive = True
			elif o in ('-s','--ssl'):
				ssl_enabled = True
	except getopt.GetoptError as err:
		print str(err)
		usage()
		sys.exit(2)

	if not args:
		print "missed LOCAL_DIRECTORY argument"
		usage()
		sys.exit(2)

	local_directory = " ".join(args)

	bot = Sinusbot(host, port, username, password, ssl_enabled)

	print local_directory

	if not os.path.isdir(local_directory):
		print 'LOCAL_DIRECTORY must be a valid directory!'
		sys.exit(1)

	if not bot.Auth():
		print 'Error on Authentication!'
		sys.exit(1)
	print 'Success Authenticated!'

	uploadHelper(os.path.abspath(local_directory), bot, recursive, base_folder_uuid)

	print 'Completed -> Uploaded %d files with %d errors.' % (bot.success_count, bot.error_count)
