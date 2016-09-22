# -*- coding: utf-8 -*-

from config import YOUR_API_KEY, here_app_id, here_app_code

separator = '&'

## This part is for Skobbler RealReach feature
url_skob = 'http://'+YOUR_API_KEY+'.tor.skobbler.net/tor/RSngx/RealReach/json/20_5/en/'+YOUR_API_KEY+'?start='

urlSkobParams = separator.join((url_skob
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

## This part is for HERE Isoline feature
url_here = 'https://isoline.route.cit.api.here.com/routing/7.2/calculateisoline.json?app_id='

urlHereParams = separator.join((url_here
                                     + here_app_id, # app id
                                    'app_code='
                                    + here_app_code,
                                    'mode=fastest;' #shortest/fastest, car/bicycle/truck,
                                    + '%s;'
                                    + 'traffic:%s', #enabled, disabled
                                    'start=geo!'
                                    + '%s', #coords
                                    'range='
                                    + '%s', 
                                    'rangetype='
                                    + '%s' # distance, time
                                    ))


## This part is for Nominatim geocoding
url_nominatim = 'http://nominatim.openstreetmap.org/reverse?format=xml'

nominatimString = separator.join((url_nominatim,
                                'lat='
                                + '%s',
                                'lon='
                                + '%s',
                                'zoom=18&addressdetails=1'))