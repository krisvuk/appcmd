import os
import re
import random
import hashlib
import urllib2
import hmac
from google.appengine.api import urlfetch
from google.appengine.api import users
from string import letters
from google.appengine.ext import blobstore
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import datetime
import webapp2
import jinja2
from google.appengine.ext import db
from HTMLParser import HTMLParser


class Get_Twitch_State(MainHandler):
	def get(self):
		self.response.out.write("""<html><body>hello</body></html>
									""")
		
	
app = webapp2.WSGIApplication([('/get_twitch_state', Get_Twitch_State)]
                              debug=True)
