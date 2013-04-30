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

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)



secret = 'ID,fmkf458FDHhfJIJ9j%^%hY77RRF76gb.2'


def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

class MainHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))



class MainPage(MainHandler):
    def get(self):
	if self.user:
            self.render('index.html', username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name)
        else:
            self.render('index.html')

    def post(self):
	username = self.request.get('username').lower()
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/')
        else:
            msg = 'Invalid username or password.'
            self.render('index.html', error = msg)	


# user stuff
def make_salt(length = 5):
    return ''.join(random.choice(letters) for x in xrange(length))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)

def valid_pw(name, password, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(name, password, salt)

def users_key(group = 'default'):
    return db.Key.from_path('users', group)

class User(db.Model):
    name = db.StringProperty(required = True)
    pw_hash = db.StringProperty(required = True)
    email = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    first_name = db.StringProperty(required = True)
    last_name = db.StringProperty(required = True)
    country = db.StringProperty(required = True)
    month = db.StringProperty(required = True)
    day = db.StringProperty(required = True)
    year =db.StringProperty(required = True)
  
  
    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = User.all().filter('name =', name).get()
        return u
    
    @classmethod
    def by_email(cls, email):
        e = User.all().filter('email =', email).get()
        return e

    @classmethod
    def register(cls, name, pw, email = None, first_name = None, last_name = None, country = None, month = None, day = None, year = None):
        pw_hash = make_pw_hash(name, pw)
        return User(parent = users_key(),
                    name = name,
                    pw_hash = pw_hash,
                    email = email,
		    first_name = first_name,
                    last_name = last_name,
                    country = country,
                    month = month,
                    day = day,
                    year = year)
	

    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.pw_hash):
            return u

class Twitch_Data(db.Model):
    name = db.StringProperty(required = True)
    twitch_state = db.TextProperty()
    created = db.DateTimeProperty(auto_now_add = True)

class Reddit_Data(db.Model):
    name = db.StringProperty(required = True)
    reddit_state = db.ListProperty(str)
    website_url = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add = True)

    @classmethod
    def by_name(cls, website_url):
        e = Reddit_Data.all().filter('website_url =', website_url).get()
        return e

    @classmethod
    def state(cls, reddit_state, website_url):
        state = check_state(reddit_state , website_url)
        return state

    @classmethod
    def by_id(cls, uid):
        return Reddit_Data.get_by_id(uid, parent = users_key())

class Streams(db.Model):
    username = db.StringProperty(required = True)
    stream_url = db.StringProperty()
    stream_name = db.StringProperty()
    stream_title = db.StringProperty()
    tracking_value = db.StringProperty()
    embedded_stream = db.TextProperty()
    streamid = db.TextProperty()
    created = db.DateTimeProperty(auto_now_add = True)

    @classmethod
    def stream_type(self, b):
        url = str(b)
        if url.find('twitch') == -1:
            return 'Own3D.tv'
        else:
            return 'Twitch.tv' 

    @classmethod
    def by_name(cls, stream_name):
        e = Streams.all().filter('stream_name =', stream_name).get()
        return e

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_title(cls, stream_title):
        e = Streams.all().filter('stream_title =', stream_title).get()
        return e

    
class Tracking_Streams(db.Model):
    username = db.StringProperty(required = True)
    stream_url = db.StringProperty()
    stream_name = db.StringProperty()
    stream_title = db.StringProperty()
    tracking_value = db.StringProperty()
    embedded_stream = db.TextProperty()
    streamid = db.TextProperty()
    created = db.DateTimeProperty(auto_now_add = True)

    @classmethod
    def stream_type(self, b):
        url = b
        if url.find('twitch') == -1:
            return 'Own3D.tv'
        else:
            return 'Twitch.tv'
    @classmethod
    def check_if_live_twitch(self, b):
        url = ('http://api.justin.tv/api/stream/summary.xml?channel=%s' %b)
        result = urlfetch.fetch(url)
        check = result.content
        if (check).find('<streams_count>1</streams_count>') == -1:
            return 'Offline'
        else:
            return 'Live'

    @classmethod
    def check_if_live_own3d(self, b):
        url = (b)
        result = urlfetch.fetch(url)
        check = result.content
        a = check.find('http://www.own3d.tv/liveembed/')
        b = check.find('"></iframe>')
        stream_id = check[a + 30:b]
        url2 = ('http://api.own3d.tv/rest/live/list')
        result2 = urlfetch.fetch(url2)
        check2 = result2.content
        if (check2).find(stream_id) == -1:
            return 'Offline'
        else:
            return 'Live'

    @classmethod
    def by_name(cls, stream_name):
        e = Tracking_Streams.all().filter('stream_name =', stream_name).get()
        return e

    @classmethod
    def by_title(cls, stream_title):
        e = Tracking_Streams.all().filter('stream_title =', stream_title).get()
        return e

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

##Regular Expressions

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASSWORD_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASSWORD_RE.match(password)

EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
def valid_email(email):
    return email and EMAIL_RE.match(email)

def reddit_posts(url):
    hdr = { 'User-Agent' : 'This is AppCMDs BOT' }
    req = urllib2.Request(url, headers=hdr)
    html = urllib2.urlopen(req).read()


    start = 0
    end = 0
    x = 0
    end_url = 0
    reddit_list = []

    while x < 25:
        start = (html.find('"clicked": false, "title":', end+4)+28)
        end = (html.find('",', start)-2)
        start_url = (html.find(' "permalink": "', end)+15)
        end_url = html.find('", "name":', start_url)
        x = x + 1
        title = html[start:end+2]
        link = "http://www.reddit.com"+str(html[start_url:end_url])
        reddit_list.append(title)
        reddit_list.append(link)

    return reddit_list


def reddit_diff(the_list, the_list2):
    number = 0
    list_diff = []
    length_of_list = len(the_list)


    for all in the_list:
        if the_list[number] not in the_list2:
            list_diff.append(the_list[number])
        number = number + 1
    
    #if len(list_diff)>3:
#
      #  list_diff.pop(-1)
      #  list_diff.pop(-1)    
        
    return list_diff


class SignUp(MainHandler):
    def get(self):
        self.render("register.html")

    def post(self):
        have_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify_password = self.request.get('verify_password')
        self.email = self.request.get('email')
	self.first_name = self.request.get('firstname')
	self.lastname = self.request.get('lastname')
	self.country = self.request.get('country')
	self.month = self.request.get('month')
	self.day = self.request.get('day')
	self.year = self.request.get('year')
	self.verify_email = self.request.get('verify_email')

        params = dict(verify_email = self.verify_email, username = self.username, email = self.email, firstname=self.first_name, verify_password = self.verify_password, lastname = self.lastname, country = self.country, month = self.month, day = self.day, year = self.year)

        if not valid_username(self.username):
            params['username_error'] = "Invalid username (or blank)."
            have_error = True

        if not valid_password(self.password):
            params['password_error'] = "That wasn't a valid password."
            have_error = True
            
        elif self.password != self.verify_password:
            params['password_verify_error'] = "Your passwords didn't match."
            have_error = True

        if not self.country:
            params['country_error'] = "Country required."
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        elif self.email != self.verify_email:
            params['error_verify_email'] = "That's not a valid email."
            have_error = True

	if not self.first_name:
	    params['error_firstname'] = "Firstname is required."
            have_error = True
            
	if not self.lastname:
	    params['error_lastname'] = "Lastname is required."
            have_error = True
            
	if not self.month:
	    params['error_birthday'] = "A birth day is required."
            have_error = True
            
	if not self.day:
	    params['error_birthday'] = "A birth day is required."
            have_error = True

	if not self.year:
	    params['error_birthday'] = "A birth day is required."
            have_error = True
            
        if have_error:
            self.render('register.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError
            

class Register(SignUp):

    def get(self):
        if self.user:
            self.redirect('/')
        else:
            self.render('register.html')
    
    def done(self):
        #make sure the user doesn't already exist
	e = User.by_email(self.email.lower())
        u = User.by_name(self.username.lower())
        if u and e:
            msg = 'That user already exists.'
            msg1 = 'That email is already in use.'
            self.render('register.html', error_username = msg, error_email = msg1)
	elif u:
            msg = 'That user already exists.'
            self.render('register.html', error_username = msg)
	elif e:
            msg1 = 'That email is already in use.'
            self.render('register.html', error_email = msg1)
        else:
            u = User.register(self.username.lower(), self.password, self.email.lower(), self.first_name, self.lastname, self.country, self.month, self.day, self.year)
            u.put()

            self.login(u)
            self.redirect('/')
	
        

class Login(MainHandler):
    def get(self):
        self.render('index.html')

    def post(self):
        username = self.request.get('username').lower()
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/news_page')
        else:
            msg = 'Invalid login. Please try again.'
            self.render('index.html', error = msg)

class Logout(MainHandler):
    def get(self):
        self.logout()
        self.redirect('/')

class Dashboard(MainHandler):
    def get(self, user_id):
	username = self.user.name
	if username == user_id:
            self.render('dashboard.html', username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name)
        else:
            self.render('error.html')
			
class Profile(MainHandler):
    def get(self, user_id):
	username = self.user.name
	if username == user_id:
            self.render('profile.html', username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name)
        else:
            self.render('error.html')
			
class Twitch(MainHandler):

    def get(self):
        twitch_data = Twitch_Data(key_name = "bot", name = "bot")
    	source_code = urlfetch.fetch('https://api.twitch.tv/kraken/streams/')
    	ascii = unicode((source_code.content), errors='ignore')
    	twitch_data.twitch_state = str(ascii)
    	twitch_data.put()
    	self.redirect('/')

class Reddit(MainHandler):

    def get(self):
        reddit_data = Reddit_Data(key_name = "bot", name = "bot")
        reddit_data.reddit_state = reddit_posts("http://www.reddit.com/r/all/hot/.json")
        reddit_data.website_url = ("http://www.reddit.com")
        reddit_data.put()
        self.redirect('/')

class Reddit_Main(MainHandler):

    def get(self, user_id):
        username = self.user.name
        website_state = ''
        reddit_posts2 = []
        reddit_posts_list = db.GqlQuery("select * from Reddit_Data WHERE name = 'bot' ")
        reddit_posts_list_user = db.GqlQuery("select * from Reddit_Data WHERE name =:1", username)
        for aaa in reddit_posts_list:
            reddit_posts = aaa.reddit_state
        for aaa in reddit_posts_list_user:
            reddit_posts2 = aaa.reddit_state
        if reddit_posts2 != []:
            post_diff = reddit_diff(reddit_posts, reddit_posts2)
        else:
            post_diff = "no comparable state"
        if username == user_id:
            self.render('reddit_main.html', reddit_posts = post_diff, reddit_posts_len = len(post_diff), username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name)
        else:
            self.render('error.html')

    def post(self, a):
        reddit_data = Reddit_Data(key_name = self.user.name, name = self.user.name)
        reddit_data.reddit_state = reddit_posts("http://www.reddit.com/r/all/hot/.json")
        reddit_data.website_url = ("http://www.reddit.com")
        reddit_data.put()
        self.redirect('/reddit_main/%s' %self.user.name)

class Streams_Main(MainHandler):

    def get(self, user_id):
	username = self.user.name
	if username == user_id:
            twitch_code = ''
            current_user = self.user.name
            tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE username =:1 ", current_user)
            streams = db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)
            twitch = db.GqlQuery("select * from Twitch_Data WHERE name = 'bot' ")
            for aaa in twitch:
                twitch_code = aaa.twitch_state
            self.render('streams_main.html', twitch_code = twitch_code, x = 0, tracking_streams = tracking_streams, streams = streams, username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name)
        else:
            self.render('error.html')


class Add_Stream(MainHandler):
    def get(self):
        if self.user:
            self.render('add_stream.html', username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name)
        else:
            self.redirect('/register')

    def post(self):
        tracking_streams = ''
        checkss2 = ''
        stream_url = self.request.get('stream_url')
        stream_title = self.request.get('stream_title')
        current_user = self.user.name
        check = db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)
        checkss = ''
        check_if_twitch = str(stream_url.find('http://www.twitch.tv/'))
        check_if_track = self.request.get('if_track')
        streams_tracking_count = (db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)).count()
        for checks in check:
            checkss = checks.stream_url
        for checks2 in check:
            checkss2 = checks2.stream_title
        if stream_url == '':
            blank_error = "You must enter a valid url and a title."
            self.render('add_stream.html', stream_url = stream_url, stream_title = stream_title, blank_error = blank_error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        elif checkss == stream_url:
            already_added_error = ("You are already tracking %s." %stream_url)
            self.render('add_stream.html', stream_url = stream_url, stream_title = stream_title, already_added_error  = already_added_error , username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        elif not check_if_track:
            check_if_track_error = ("You did not elect to track or not track this stream.")
            self.render('add_stream.html', stream_url = stream_url, stream_title = stream_title, check_if_track_error = check_if_track_error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)

        elif not stream_title:
            error = ("You did not enter a valid stream title (3-12 characters).")
            self.render('add_stream.html',stream_url = stream_url, stream_title = stream_title,  error = error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
            
        elif checkss2 == stream_title:
            title_error = ("You have already used the name %s. " %stream_title)
            self.render('add_stream.html',stream_url = stream_url, stream_title = stream_title,  title_error = title_error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)

        elif stream_title.find(' ') != -1:
            space_error = ("Your title cannot have any spaces.")
            self.render('add_stream.html',stream_url = stream_url, stream_title = stream_title,  space_error = space_error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
            
        elif len(stream_title) > 14:
            title_length_error = ("Your title cannot be over 14 characters.")
            self.render('add_stream.html',stream_url = stream_url, stream_title = stream_title,  title_length_error = title_length_error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        elif check_if_track == "True" and int(streams_tracking_count) >= 12:
            error = ("You cannot track more than 12 streams.")
            self.render('add_stream.html',stream_url = stream_url, stream_title = stream_title,  error = error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        elif check_if_twitch == "0":
            if check_if_track == "True":
                tracking_streams = Tracking_Streams(username = self.user.name)
                streamupl = self.request.get('stream_url')
                tracking_streams.stream_url = (streamupl)
                stream_nameupl = self.request.get('stream_url')
                tracking_streams.stream_name = (stream_nameupl[(stream_nameupl.find('.tv/')+ 4):])
                stream_track = self.request.get('if_track')
                tracking_streams.tracking_value = (stream_track)
                stream_titleupl = self.request.get('stream_title')
                tracking_streams.embedded_stream = ('<object type="application/x-shockwave-flash" height="365" width="598" id="live_embed_player_flash" data="http://www.twitch.tv/widgets/live_embed_player.swf?channel=%s" bgcolor="#000000"><param name="allowFullScreen" value="true" /><param name="allowScriptAccess" value="always" /><param name="allowNetworking" value="all" /><param name="movie" value="http://www.twitch.tv/widgets/live_embed_player.swf" /><param name="flashvars" value="hostname=www.twitch.tv&channel=%s&auto_play=true&start_volume=25" /></object>' %(tracking_streams.stream_name, tracking_streams.stream_name))
                tracking_streams.stream_title = (stream_titleupl)
                tracking_streams.put()
                self.redirect('/streams_main/%s' %self.user.name)
            else:
                streams = Streams(username = self.user.name)
                streamupl = self.request.get('stream_url')
                streams.stream_url = (streamupl)
                stream_nameupl = self.request.get('stream_url')
                streams.stream_name = (stream_nameupl[(stream_nameupl.find('.tv/')+ 4):])
                stream_track = self.request.get('if_track')
                streams.tracking_value = (stream_track)
                stream_titleupl = self.request.get('stream_title')
                streams.embedded_stream = ('<object type="application/x-shockwave-flash" height="365" width="598" id="live_embed_player_flash" data="http://www.twitch.tv/widgets/live_embed_player.swf?channel=%s" bgcolor="#000000"><param name="allowFullScreen" value="true" /><param name="allowScriptAccess" value="always" /><param name="allowNetworking" value="all" /><param name="movie" value="http://www.twitch.tv/widgets/live_embed_player.swf" /><param name="flashvars" value="hostname=www.twitch.tv&channel=%s&auto_play=true&start_volume=25" /></object>' %(streams.stream_name, streams.stream_name))
                streams.stream_title = (stream_titleupl)
                streams.put()
                self.redirect('/streams_main/%s' %self.user.name)
        else:
            error = "You must enter a valid url (own3d.tv or twitch.tv)."
            self.render('add_stream.html', stream_url = stream_url, stream_title = stream_title,  error = error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)

class Stream_One(MainHandler):
    def get(self, stream_one):
        if self.user:
            stream_bed1 = ''
            current_user = str(self.user.name)
            streams = db.GqlQuery("select * from Streams WHERE username =:1", current_user)
            tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)
            streams2 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_one)
            tracking_streams2 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_one)
            e = Streams.by_title(stream_one)
            f = Tracking_Streams.by_title(stream_one)
            if e:
                for stream_ in streams2:
                    stream_bed1 = stream_.embedded_stream
            elif f:
                for tracking_ in tracking_streams2:
                    stream_bed1 = tracking_.embedded_stream
            self.render('stream_one.html', stream_bed1 = stream_bed1, tracking_streams = tracking_streams, streams = streams, stream_one = stream_one, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        else:
            redirect('/register')

    def post(self, stream_one):
        stream_two_name = self.request.get("stream_from_two")
        self.redirect('/stream_two/%s/%s' %(stream_one, stream_two_name))

class Stream_Two(MainHandler):
    def get(self, stream_one, stream_two):
        if self.user:
            stream_bed1 = ''
            stream_bed2 = ''
            current_user = str(self.user.name)
            tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)
            streams = db.GqlQuery("select * from Streams WHERE username =:1", current_user)
            
            streams2 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_one)
            tracking_streams2 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_one)
            
            streams3 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_two)
            tracking_streams3 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_two)
            
            e = Streams.by_title(stream_one)
            f = Tracking_Streams.by_title(stream_one)
            if e:
                for stream_ in streams2:
                    stream_bed1 = stream_.embedded_stream
            elif f:
                for tracking_ in tracking_streams2:
                    stream_bed1 = tracking_.embedded_stream

            e2 = Streams.by_title(stream_two)
            f2 = Tracking_Streams.by_title(stream_two)
            if e2:
                for stream_ in streams3:
                    stream_bed2 = stream_.embedded_stream
            elif f2:
                for tracking_ in tracking_streams3:
                    stream_bed2 = tracking_.embedded_stream
            self.render('stream_two.html', stream_bed1 = stream_bed1, stream_bed2 = stream_bed2, tracking_streams = tracking_streams, streams = streams, stream_two = stream_two, stream_one = stream_one, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        else:
            redirect('/register')

    def post(self, stream_one, stream_two):
        stream_three_name = self.request.get("stream_from_three")
        self.redirect('/stream_three/%s/%s/%s' %(stream_one, stream_two, stream_three_name))

class Stream_Three(MainHandler):
    def get(self, stream_one, stream_two, stream_three):
        if self.user:
            stream_bed1 = ''
            stream_bed2 = ''
            stream_bed3 = ''
            current_user = str(self.user.name)
            tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)
            streams = db.GqlQuery("select * from Streams WHERE username =:1", current_user)
            
            streams2 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_one)
            tracking_streams2 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_one)
            
            streams3 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_two)
            tracking_streams3 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_two)

            streams4 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_three)
            tracking_streams4 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_three)
            
            e = Streams.by_title(stream_one)
            f = Tracking_Streams.by_title(stream_one)
            if e:
                for stream_ in streams2:
                    stream_bed1 = stream_.embedded_stream
            elif f:
                for tracking_ in tracking_streams2:
                    stream_bed1 = tracking_.embedded_stream

            e2 = Streams.by_title(stream_two)
            f2 = Tracking_Streams.by_title(stream_two)
            if e2:
                for stream_ in streams3:
                    stream_bed2 = stream_.embedded_stream
            elif f2:
                for tracking_ in tracking_streams3:
                    stream_bed2 = tracking_.embedded_stream

            e3 = Streams.by_title(stream_three)
            f3 = Tracking_Streams.by_title(stream_three)
            if e3:
                for stream_ in streams4:
                    stream_bed3 = stream_.embedded_stream
            elif f3:
                for tracking_ in tracking_streams4:
                    stream_bed3 = tracking_.embedded_stream
            self.render('stream_three.html', stream_bed1 = stream_bed1, stream_bed2 = stream_bed2, stream_bed3 = stream_bed3, tracking_streams = tracking_streams, streams = streams, stream_three = stream_three, stream_two = stream_two, stream_one = stream_one, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        else:
            redirect('/register')

    def post(self, stream_one, stream_two, stream_three):
        stream_four_name = self.request.get("stream_from_three")
        self.redirect('/stream_four/%s/%s/%s/%s' %(stream_one, stream_two, stream_three, stream_four_name))

class Stream_Four(MainHandler):
    def get(self, stream_one, stream_two, stream_three, stream_four):
        if self.user:
            stream_bed1 = ''
            stream_bed2 = ''
            stream_bed3 = ''
            stream_bed4 = ''
            current_user = str(self.user.name)
            streams2 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_one)
            tracking_streams2 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_one)
            
            streams3 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_two)
            tracking_streams3 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_two)

            streams4 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_three)
            tracking_streams4 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_three)

            streams5 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_four)
            tracking_streams5 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_four)
            
            e = Streams.by_title(stream_one)
            f = Tracking_Streams.by_title(stream_one)
            if e:
                for stream_ in streams2:
                    stream_bed1 = stream_.embedded_stream
            elif f:
                for tracking_ in tracking_streams2:
                    stream_bed1 = tracking_.embedded_stream

            e2 = Streams.by_title(stream_two)
            f2 = Tracking_Streams.by_title(stream_two)
            if e2:
                for stream_ in streams3:
                    stream_bed2 = stream_.embedded_stream
            elif f2:
                for tracking_ in tracking_streams3:
                    stream_bed2 = tracking_.embedded_stream

            e3 = Streams.by_title(stream_three)
            f3 = Tracking_Streams.by_title(stream_three)
            if e3:
                for stream_ in streams4:
                    stream_bed3 = stream_.embedded_stream
            elif f3:
                for tracking_ in tracking_streams4:
                    stream_bed3 = tracking_.embedded_stream

            e4 = Streams.by_title(stream_four)
            f4 = Tracking_Streams.by_title(stream_four)
            if e4:
                for stream_ in streams5:
                    stream_bed4 = stream_.embedded_stream
            elif f4:
                for tracking_ in tracking_streams5:
                    stream_bed4 = tracking_.embedded_stream
            self.render('stream_four.html', stream_bed1 = stream_bed1, stream_bed2 = stream_bed2, stream_bed3 = stream_bed3, stream_bed4 = stream_bed4, stream_four = stream_four, stream_three = stream_three, stream_two = stream_two, stream_one = stream_one, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        else:
            redirect('/register')

class My_Streams_List(MainHandler):
    def get(self):
        tracking_streams = ''
        current_user = self.user.name
        streams = db.GqlQuery("select * from Streams WHERE username =:1", current_user)
        tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)
        streams_tracking_count = (db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)).count()
        streams_count2 = (db.GqlQuery("select * from Streams WHERE username =:1", current_user)).count()
        self.render('stream_manager.html', streams_count = (streams_tracking_count+streams_count2), streams_tracking_count = streams_tracking_count, tracking_streams = tracking_streams, streams = streams, username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name)

    def post(self):
        current_user = self.user.name
        streams_tracking_count = (db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)).count()
        if self.request.get('untrack'):
            stream_url1 = ''
            stream_name1 = ''
            stream_title1 = ''
            stream_tracking_value1 = ''
            stream_embedded_stream1 = ''
            current_user = self.user.name
            stream_id = self.request.get('url')
            tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE stream_url =:1", stream_id)
            for stream_url_ in tracking_streams:
                stream_url1 = stream_url_.stream_url
            for stream_name_ in tracking_streams:
                stream_name1 = stream_name_.stream_name
            for stream_title_ in tracking_streams:
                stream_title1 = stream_title_.stream_title
            for stream_tracking_value_ in tracking_streams:
                stream_tracking_value1 = stream_tracking_value_.tracking_value
            for stream_embedded_stream_ in tracking_streams:
                stream_embedded_stream1 = stream_embedded_stream_.embedded_stream
            streams = Streams(username = self.user.name, stream_url = stream_url1, stream_name = stream_name1, stream_title = stream_title1, tracking_value = 'False', embedded_stream = stream_embedded_stream1)
            streams.put()
            the_stream = self.request.get('untrack')
            q = Tracking_Streams.get_by_id(int(the_stream), parent=None)
            db.delete(q)
            self.redirect('/stream_manager')
        elif self.request.get('track'):
            if int(streams_tracking_count) >= 12:
                tracking_streams = ''
                current_user = self.user.name
                streams = db.GqlQuery("select * from Streams WHERE username =:1", current_user)
                tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)
                streams_tracking_count = (db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)).count()
                streams_count2 = (db.GqlQuery("select * from Streams WHERE username =:1", current_user)).count()
                self.redirect('/stream_manager')
            else:    
                stream_url2 = ''
                stream_name2 = ''
                stream_title2 = ''
                stream_tracking_value2 = ''
                stream_embedded_stream2 = ''
                tracking_streams = ''
                current_user = self.user.name
                stream_id = self.request.get('url2')
                streams = db.GqlQuery("select * from Streams WHERE stream_url =:1", stream_id)
                for stream_url_ in streams:
                    stream_url2 = stream_url_.stream_url
                for stream_name_ in streams:
                    stream_name2 = stream_name_.stream_name
                for stream_title_ in streams:
                    stream_title2 = stream_title_.stream_title
                for stream_tracking_value_ in streams:
                    stream_tracking_value2 = stream_tracking_value_.tracking_value
                for stream_embedded_stream_ in streams:
                    stream_embedded_stream2 = stream_embedded_stream_.embedded_stream
                tracking_streams = Tracking_Streams(username = self.user.name, stream_url = stream_url2, stream_name = stream_name2, stream_title = stream_title2, tracking_value = 'True', embedded_stream = stream_embedded_stream2)
                tracking_streams.put()
                the_stream = self.request.get('track')
                q = Streams.get_by_id(int(the_stream), parent=None)
                db.delete(q)
                self.redirect('/stream_manager')
        elif self.request.get('delete_untracked'):
            stream_url2 = ''
            stream_name2 = ''
            stream_title2 = ''
            stream_tracking_value2 = ''
            stream_embedded_stream2 = ''
            tracking_streams = ''
            current_user = self.user.name
            stream_id = self.request.get('url2')
            streams = db.GqlQuery("select * from Streams WHERE stream_url =:1", stream_id)
            for stream_url_ in streams:
                stream_url2 = stream_url_.stream_url
            for stream_name_ in streams:
                stream_name2 = stream_name_.stream_name
            for stream_title_ in streams:
                stream_title2 = stream_title_.stream_title
            for stream_tracking_value_ in streams:
                stream_tracking_value2 = stream_tracking_value_.tracking_value
            for stream_embedded_stream_ in streams:
                stream_embedded_stream2 = stream_embedded_stream_.embedded_stream
            tracking_streams = Tracking_Streams(username = self.user.name, stream_url = stream_url2, stream_name = stream_name2, stream_title = stream_title2, tracking_value = 'True', embedded_stream = stream_embedded_stream2)
            the_stream = self.request.get('delete_untracked')
            q = Streams.get_by_id(int(the_stream), parent=None)
            db.delete(q)
            self.redirect('/stream_manager')
        elif self.request.get('delete_tracked'):
            stream_url1 = ''
            stream_name1 = ''
            stream_title1 = ''
            stream_tracking_value1 = ''
            stream_embedded_stream1 = ''
            current_user = self.user.name
            stream_id = self.request.get('url')
            tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE stream_url =:1", stream_id)
            for stream_url_ in tracking_streams:
                stream_url1 = stream_url_.stream_url
            for stream_name_ in tracking_streams:
                stream_name1 = stream_name_.stream_name
            for stream_title_ in tracking_streams:
                stream_title1 = stream_title_.stream_title
            for stream_tracking_value_ in tracking_streams:
                stream_tracking_value1 = stream_tracking_value_.tracking_value
            for stream_embedded_stream_ in tracking_streams:
                stream_embedded_stream1 = stream_embedded_stream_.embedded_stream
            streams = Streams(username = self.user.name, stream_url = stream_url1, stream_name = stream_name1, stream_title = stream_title1, tracking_value = 'False', embedded_stream = stream_embedded_stream1)
            the_stream = self.request.get('delete_tracked')
            q = Tracking_Streams.get_by_id(int(the_stream), parent=None)
            db.delete(q)
            self.redirect('/stream_manager')
            
app = webapp2.WSGIApplication([('/', MainPage),
                               ('/logout', Logout),
                               ('/register', Register),
                               ('/login', Login),
			                   ('/dashboard/(.*)', Dashboard),
			                   ('/profile/(.*)', Profile),
			                   ('/twitch', Twitch),
                               ('/reddit', Reddit),
                               ('/streams_main/(.*)', Streams_Main),
                               ('/reddit_main/(.*)', Reddit_Main),
                               ('/add_stream', Add_Stream),
                               ('/stream_one/(.*)', Stream_One),
                               ('/stream_two/(.*)/(.*)', Stream_Two),
                               ('/stream_three/(.*)/(.*)/(.*)', Stream_Three),
                               ('/stream_four/(.*)/(.*)/(.*)/(.*)', Stream_Four),
                               ('/stream_manager', My_Streams_List)],
                              debug=True)
