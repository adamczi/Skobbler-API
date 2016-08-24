# -*- coding: utf-8 -*-

from config import YOUR_API_KEY

separator = '&'

## This part is for RealReach feature
url_skob = 'http://'+YOUR_API_KEY+'.tor.skobbler.net/tor/RSngx/RealReach/json/20_5/en/'+YOUR_API_KEY+'?start='

urlWithParams = separator.join((url_skob
                                     + '%s',
                                    'transport='
                                    + '%s',
                                    'range='
                                    + '%s',
                                    'units='
                                    + '%s',
                                    '%s',
                                    '%s',
                                    'nonReachable=0',
                                    'response_type=gps'))

## This part is for Nominatim geocoding
url_nominatim = 'http://nominatim.openstreetmap.org/reverse?format=xml'

nominatimString = separator.join((url_nominatim,
                                'lat='
                                + '%s',
                                'lon='
                                + '%s',
                                'zoom=18&addressdetails=1'))