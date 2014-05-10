#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yang Gao <gaoyang.public@gmail.com>
# vim: ts=4 et ai

import sys
import requests 
import json
import time
import datetime
import yaml
import sqlite3
from requests_oauthlib import OAuth1Session

TRADEME_BASE_API = 'http://api.trademe.co.nz/v1/Search/%s.json'
CONSUMER_KEY     = ''
CONSUMER_SECRET  = ''
OAUTH_TOKEN_SECRET = ''
OAUTH_TOKEN      = ''


def json_encode(s):
    return json.dumps(s, separators=(',',':'))

def json_decode(s):
    return json.loads(s)

class Trademe(object):
    trademe = requests

    def __init__(self):
        pass

    def _authenticate(self, consumer_key, 
                           consumer_secret):
#                           oauth_token, 
#                           oauth_secret):
        request_token_url = 'https://secure.trademe.co.nz/Oauth/RequestToken?scope=MyTradeMeRead,MyTradeMeWrite'
        authorization_base_url = 'https://secure.trademe.co.nz/Oauth/Authorize'
        access_token_url = 'https://secure.trademe.co.nz/Oauth/AccessToken'
        kw = dict()
        kw['client_secret']=consumer_secret
        #kw['resource_owner_key']=oauth_token
        #kw['resource_owner_secret']=oauth_secret
        self.trademe = OAuth1Session(consumer_key, **kw) 
        self.trademe.fetch_request_token(request_token_url)
        authorization_url = self.trademe.authorization_url(authorization_base_url)
        print(authorization_url)
        redirect_response = raw_input('Paste the full redirect URL here:')
        self.trademe.parse_authorization_response(redirect_response)
        oauthxx = self.trademe.fetch_access_token(access_token_url)
        print oauthxx
	
    def authenticate(self, consumer_key, 
                           consumer_secret,
                           oauth_token, 
                           oauth_secret):
        kw = dict()
        kw['client_secret'] = consumer_secret
        kw['resource_owner_key'] = oauth_token
        kw['resource_owner_secret'] = oauth_secret
        self.trademe = OAuth1Session(consumer_key, **kw) 
	

    def getListings(self, api_path="General", 
                          feedback_func=None, **kw):

        api = TRADEME_BASE_API % api_path
        result = None

        params = dict(kw)
        try:
            resp = self.trademe.get(api, params=params, timeout=30)
            result = resp.json()
        except Exception as e:
            raise

        if not feedback_func is None:
            result = feedback_func(result)
        return result

    def getMyWatchList(self):
        api = 'https://api.trademe.co.nz/v1/MyTradeMe/Watchlist/All.json'
        try:
            resp = self.trademe.get(api)
            result = resp.json()
        except Exception as e:
            raise
        return result

def feedback_searching_result(data):
    def _collect(raw_listing):
        listing = filter(lambda x: x[0] in f_keys, 
                              raw_listing.items())
        listing = dict(listing)
        listing['ListingUrl'] = listing_url % listing['ListingId'] 

        which_category = filter(lambda c: 
                            c['Category'] == listing['Category'],
                            data['FoundCategories'])
        try:
            listing['CategoryName'] = which_category[0]['Name']
        except IndexError as e:
            listing['CategoryName'] = ''

        return listing

    listing_url = 'http://www.trademe.co.nz/Browse/Listing.aspx?id=%s'
    f_keys = ['ListingId', 'Title', 'Category', 'PictureHref', 
              'Region', 'Suburb', 'PriceDisplay', 'StartPrice',
              'BuyNowPrice']
    ret = map(_collect, data['List'])
    return ret

def getConfig(cfile):
    def _merge(data):
        config = dict()
        for item, value in data.items():
            if item.startswith('.'): continue
            config[item] = value.copy()
            if value.has_key('.include'):
                included = dict(data[value['.include']])
                config[item] = dict(included, **config[item])
                del config[item]['.include']
        return config
            
    config = dict()
    try:
        with open(cfile, 'rb') as f:
            resource = yaml.load(f.read())
            config = _merge(resource)
            f.close()
    except IOError as e:
        print str(e)
        sys.exit(2)
    except KeyError as e:
        print 'Include config(%s) does not exist.' % str(e)
        sys.exit(3)
    except Exception as e:
        raise
    return config

def sendEmail(smtp, user, passwd, me, send_to,
               subject, content, cc_to=None):
    '''
    @smtp SMTP server ip or domain.formart: "smtp.gmail.com:587"
    @user SMTP login user name.
    @passwd SMTP login password.
    @me display this string at "from" when he received mail.
    @to send to who.
    @subject email subject
    @content email content
    '''
    import email
    import mimetypes
    from email.MIMEMultipart import MIMEMultipart
    from email.MIMEText import MIMEText
    from email.MIMEImage import MIMEImage
    from email.Header import Header
    from email.utils import COMMASPACE,formatdate import smtplib

    assert(isinstance(send_to, list))
    smtp_host, smtp_port = smtp.split(":")

    toAll = list()
    msg = MIMEText(content.encode('utf-8'), 'html', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = me
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)

    [toAll.append(i) for i in send_to]

    if cc_to:
        msg['Cc'] = COMMASPACE.join(cc_to)
        [toAll.append(i) for i in cc_to]

    mailServer = smtplib.SMTP(smtp_host, smtp_port)
    mailServer.ehlo()
    mailServer.starttls()
    mailServer.ehlo()
    mailServer.login(user, passwd)
    mailServer.sendmail(user, toAll, msg.as_string())
    mailServer.close()


def template(data):
    pass

class ListingModel(object):
    TABLE = 'TradeMe'

    SQL_CREATE_TABLE = '''
CREATE TABLE IF NOT EXISTS %(tb)s(id INTEGER PRIMARY KEY DESC, title, price, buynow, category, url, pic, region, suburb, md5);
CREATE UNIQUE INDEX TradeMe_md5 ON %(tb)s(md5);
'''

    SQL_SELECT_LISTING = 'SELECT id FROM %(tb)s WHERE md5=%(md5)s;'

    def __init__(self):
        self.db = self._conn('trademe.db')
        c = self.db.cursor()
        c.executescript(self.SQL_CREATE_TABLE % dict( tb = self.TABLE))

    def _conn(self, database):
        conn = sqlite3.connect(database)
        return conn

    def save(self, listing):
        assert(isinstance(listing, dict))
        sql = "INSERT INTO %(tb)s VALUES('%(id)s', '')"

    def search(self):
        pass

def main():
    trademe = Trademe()
    #trademe._authenticate(CONSUMER_KEY, CONSUMER_SECRET)
    #                      OAUTH_TOKEN, OAUTH_SECRET)
    trademe.authenticate(CONSUMER_KEY, CONSUMER_SECRET,
                          OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
    watch_list = trademe.getMyWatchList()
    config = getConfig('prod.yaml')
    params = config.get('search_trailer_in_farming')
    func = feedback_searching_result
    listings = trademe.getListings(feedback_func=func, **params)

    #SMTP='smtp.gmail.com:587'
    #SMTP_USER = ''
    #SMTP_PASS = ''
    #ME = 'TradeMePostman'
    #SEND_TO = ['']
    #SUBJECT = 'TEST SEND MAIL'
    #CONTENT = '<html><body>hello.</body></html>'
    
    

    #sendEmail(SMTP, SMTP_USER, SMTP_PASS,
    #          ME, SEND_TO, SUBJECT, CONTENT)
    

if __name__ == '__main__':
    main()
