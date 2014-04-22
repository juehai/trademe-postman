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
from requests_oauthlib import OAuth1Session

TRADEME_BASE_API = 'http://api.trademe.co.nz/v1/Search/%s.json'
CONSUMER_KEY     = ''
CONSUMER_SECRET  = ''
OAUTH_TOKEN      = ''
OAUTH_SECRET     = ''

def json_encode(s):
    return json.dumps(s, separators=(',',':'))

def json_decode(s):
    return json.loads(s)

class Trademe(object):
    trademe = requests

    def __init__(self):
        pass

    def authenticate(self, consumer_key, 
                           consumer_secret, 
                           oauth_token, 
                           oauth_secret):
        kw = dict()
        kw['client_secret']=consumer_secret
        kw['resource_owner_key']=oauth_token
        kw['resource_owner_secret']=oauth_secret
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


def main():
    trademe = Trademe()
    trademe.authenticate(CONSUMER_KEY, CONSUMER_SECRET,
                         OAUTH_KEY, OAUTH_SECRET)
    config = getConfig('prod.yaml')
    params = config.get('search_trailer_in_farming')
    func = feedback_searching_result
    listings = trademe.getListings(feedback_func=func, **params)
    import pprint
    pprint.pprint(listings)
    

if __name__ == '__main__':
    main()
