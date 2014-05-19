#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yang Gao <gaoyang.public@gmail.com>
# vim: ts=4 et

import sys
import re
import requests 
import json
import time
import yaml
import sqlite3
import logging
from requests_oauthlib import OAuth1Session
from mako.template import Template

TRADEME_BASE_API = 'http://api.trademe.co.nz/v1/Search/%s.json'
CONSUMER_KEY     = ''
CONSUMER_SECRET  = ''
OAUTH_TOKEN_SECRET = ''
OAUTH_TOKEN      = ''


def json_encode(s):
    return json.dumps(s, separators=(',',':'))

def json_decode(s):
    return json.loads(s)

def md5(s):
    import hashlib
    m = hashlib.md5()
    m.update(s)
    return m.hexdigest()

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
        log.info('Authorization url: %s' % authorization_url)
        redirect_response = raw_input('Paste the full redirect URL here:')
        self.trademe.parse_authorization_response(redirect_response)
        oauthxx = self.trademe.fetch_access_token(access_token_url)
        log.info('oauth token: %s' % authxx)
    
    def authenticate(self, consumer_key, 
                           consumer_secret,
                           oauth_token, 
                           oauth_secret):
        kw = dict()
        kw['client_secret'] = consumer_secret
        kw['resource_owner_key'] = oauth_token
        kw['resource_owner_secret'] = oauth_secret
        self.trademe = OAuth1Session(consumer_key, **kw) 
        log.info('TradeMe authenticate successfuly.')
    

    def getListings(self, api_path="General", 
                          feedback_func=None, **kw):

        api = TRADEME_BASE_API % api_path
        result = list()
        params = dict(kw)
        try:
            resp = self.trademe.get(api, params=params, timeout=30)
            result = resp.json()
        except Exception as e:
            log.warning('Invalid TradeMe response.')

        if result and not feedback_func is None:
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

        # fix column format
        if listing.has_key('BuyNowPrice'):
            listing['BuyNowPrice'] = '$%s' % listing['BuyNowPrice']
        else:
            listing['BuyNowPrice'] = '-'
        if not listing.has_key('PriceDisplay'):
            listing['PriceDisplay'] = '-'
        if not listing.has_key('PictureHref'):
           listing['PictureHref'] = 'http://www.trademe.co.nz/images/NewSearchCards/LVIcons/hasPhoto_160x120.png'


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

    try:
        ret = map(_collect, data['List'])
    except KeyError as e:
        log.error('List not in response.')
        log.error('response: %s' % data)
        raise Exception('Response not has "List" key.')
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
            sys, search = yaml.load_all(f.read())
            config['system'] = sys
            config['search'] = _merge(search)
            f.close()
    except IOError as e:
        log.error(str(e))
        sys.exit(2)
    except KeyError as e:
        log.error('Include config(%s) does not exist.' % str(e))
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
    import smtplib
    from email.MIMEMultipart import MIMEMultipart
    from email.MIMEText import MIMEText
    from email.MIMEImage import MIMEImage
    from email.Header import Header
    from email.utils import COMMASPACE,formatdate 

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

def check_sensitive_time():
    import re
    from pytz import timezone
    from datetime import datetime

    if SENSITIVE_TIMEZONE is None or SENSITIVE_TIME is None:
        return False

    regex = re.compile(r'^(\d?\d:?\d\d)-(\d?\d:?\d\d)$')
    t1, t2 = regex.findall(SENSITIVE_TIME)[0]
    t1 = t1.replace(":", "")
    t2 = t2.replace(":", "")

    tz = timezone(SENSITIVE_TIMEZONE)
    now = datetime.now(tz)
    t3 = '%02i%02i' % (now.hour, now.minute)

    if ( t1 < t2 ):
        if ( ( t1 <= t3 ) and ( t3 <= t2 ) ):
            msg = 'Current time %s matched %s%s during test: %s'
            log.warning(msg % (t3, t1, t2, SENSITIVE_TIME))
            return True

    else:
        if ( ( t3 >= t1 ) or ( t3 <= t2 ) ):
            msg = 'Current time %s matched %s%s during test: %s'
            log.warning(msg % (t3, t1, t2, SENSITIVE_TIME))
            return True
    return False

class ListingModel(object):
    TABLE = 'TradeMe'

    SQL_CREATE_TABLE = '''
CREATE TABLE IF NOT EXISTS %(tb)s(id INTEGER PRIMARY KEY DESC, title, price, buynow, category, url, pic, region, suburb, md5, uptime TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE UNIQUE INDEX IF NOT EXISTS TradeMe_md5 ON %(tb)s(md5);
'''
    def __init__(self):
        self.db = self._conn('trademe.db')
        c = self.db.cursor()
        c.executescript(self.SQL_CREATE_TABLE % dict( tb = self.TABLE))

    def _conn(self, database):
        conn = sqlite3.connect(database)
        return conn

    def _make_md5(self, listing):
        md5sum =  md5('%s-%s' % ( listing['ListingId'],
                               listing['BuyNowPrice']))
        return md5sum

    def save(self, listing):
        assert(isinstance(listing, dict))
        fields = ['id', 'title', 'price', 'buynow',
                  'category', 'url', 'pic', 'region',
                  'suburb', 'md5']
    
        sql = "REPLACE INTO %s(%s) VALUES(%s);" % (self.TABLE, 
                ', '.join(map(lambda x: "%s" % x, fields)),
                ', '.join(map(lambda x: "?", fields)))
    
        try:
            data = (
                    listing['ListingId'],
                    listing['Title'],
                    listing['PriceDisplay'],
                    listing['BuyNowPrice'],
                    listing['Category'],
                    listing['ListingUrl'],
                    listing['PictureHref'],
                    listing['Region'],
                    listing['Suburb'],
                    self._make_md5(listing),
                    )
        except KeyError as e:
            raise Exception("%s.(data: %s)" % (str(e), listing))

        c = self.db.cursor()
        c.execute(sql, data)
        self.db.commit()

    def is_exist(self, listing):
        sql = "SELECT md5 FROM %s WHERE md5='%s'"
        sql = sql % (self.TABLE, self._make_md5(listing))
        log.debug("SQL: %s" % sql)
        c = self.db.cursor()
        c.execute(sql)
        ret = [record[0] for record in c.fetchall()]
        if not ret:
            return False
        return True

def main():
    log.info('Start init trademe.')
    trademe = Trademe()
    #trademe._authenticate(CONSUMER_KEY, CONSUMER_SECRET)
    #                      OAUTH_TOKEN, OAUTH_SECRET)
    #watch_list = trademe.getMyWatchList()
    log.info('Authenticate TradeMe API.')
    trademe.authenticate(CONSUMER_KEY, CONSUMER_SECRET,
                         OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

    for key, value in config['search'].items():
        log.info('Geting %s listing.' % key)
        params = value
        func = feedback_searching_result
        listings = trademe.getListings(feedback_func=func, **params)
        send_row = list()
        for row in listings:
            try:
                obj_listing = ListingModel()
                log.debug('save listing: %s' % row)
                if not obj_listing.is_exist(row):
                    send_row.append(row)
                # update listing to database
                obj_listing.save(row)
            except sqlite3.IntegrityError as e:
                if not str(e) == 'column md5 is not unique':
                    raise
            finally:
                # close db
                obj_listing.db.close()

        ## template    = Template(filename='template/listing.htm')
        ## print template.render(listings=listings).encode('utf-8')
        ## sys.exit()
                
        if send_row:
            template    = Template(filename='template/listing.htm')
            SUBJECT = 'EltonPostman "%s"' % key
            CONTENT     = template.render(listings=send_row)
            sendEmail(SMTP, SMTP_USER, SMTP_PASS,
                       ME, SEND_TO, SUBJECT, CONTENT)
            log.info('Sending email to %s done.' % SEND_TO)
        else:
            log.info('No update Listing in this round.')

if __name__ == '__main__':
    config = getConfig('prod.yaml')
    SMTP        = config['system'].get('SMTP_HOST')
    SMTP_USER   = config['system'].get('SMTP_USER')
    SMTP_PASS   = config['system'].get('SMTP_PASS')
    ME          = config['system'].get('DISPLAY_ME')
    SEND_TO     = config['system'].get('SEND_TO')

    CONSUMER_KEY        = config['system'].get('CONSUMER_KEY')
    CONSUMER_SECRET     = config['system'].get('CONSUMER_SECRET')
    OAUTH_TOKEN         = config['system'].get('OAUTH_TOKEN')
    OAUTH_TOKEN_SECRET  = config['system'].get('OAUTH_TOKEN_SECRET')

    INTERVAL = config['system'].get('INTERVAL', 60)

    SENSITIVE_TIMEZONE = config['system'].get('SENSITIVE_TIMEZONE', None)
    SENSITIVE_TIME = config['system'].get('SENSITIVE_TIME', None)

    FORMAT = '%(levelname)s: %(message)s'
    logging.basicConfig(format=FORMAT)
    log = logging.getLogger('postman')
    log_level = getattr(logging, config['system'].get('LOG_LEVEL', 'INFO'))
    log.setLevel(log_level)

    # for daemontools
    while True:
        try:
            if check_sensitive_time(): continue
            main()
        except Exception as e:
            log.error('v'*80)
            log.exception('Got exception on main handler')
            log.error('^'*80)
            SUBJECT = '[Warning]EltonPostman crashed'
            CONTENT = 'Message: %s' % str(e)
            sendEmail(SMTP, SMTP_USER, SMTP_PASS,
                       ME, SEND_TO, SUBJECT, CONTENT)
            log.debug('Send error email done.')
        finally:
            log.info('All done. Sleep %d second(s)..' % INTERVAL)
            time.sleep(INTERVAL)
