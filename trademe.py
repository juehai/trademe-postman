#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yang Gao <gaoyang.public@gmail.com>
# vim: ts=4 et ai

import requests 
from requests_oauthlib import OAuth1Session
import json
import time
import datetime

TRADEME_BASE_API = 'http://api.trademe.co.nz/v1/Search/%s.json'

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

def main():
    trademe = Trademe()
    params = dict()
    params['buy'] = 'All'
    params['category'] = 1259
    params['condition'] = 'Used'
    params['expired'] = 'false'
    params['pay'] = 'All'
    params['photo_size'] = 'Large'
    params['return_metadata'] = 'false'
    params['page'] = '1'
    params['row'] = '25'
    params['shipping_method'] = 'All'
    params['sort_order'] = 'ExpiryDesc'
    func = feedback_searching_result
    listings = trademe.getListings(feedback_func=func, **params)
    import pprint
    pprint.pprint(listings)
    

if __name__ == '__main__':
    main()
