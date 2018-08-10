#!/usr/bin/env python
'''Benchmark geocoder wrapper service'''

# @package geocoder.web.geocoder_svc.Pygmalion
#
# @brief Benchmark geocoder wrapper service
#
# RIGHTS AND RESTRICTIONS:
#
# @copyright 2014 Atmospheric and Environmental Research (AER), Inc.
#
# This software was authored by Atmospheric and Environmental Research Inc.
# employees and is, therefore, subject to the following:
#
# - The information and source code contained herein is provided as is
# with no warranty expressed or implied.
#
# - The information and source code contained herein is the exclusive
# property of Atmospheric and Environmental Research Inc. and may not be disclosed,
# or reproduced in whole or in part without explicit written authorization
# from the company.
#
# CLASSIFICATION:
#
#     None
#
# CONTACT:
#
#   Atmospheric & Environmental Research, Inc.
#   131 Hartwell Ave.
#   Lexington, MA 02421-3126 USA
#   Phone: 781.761.2288
#
# @author Mike Sze: msze@aer.com

import logging
import logging.config
import argparse
import pkg_resources

import json

from flask import Flask
from flask import request, make_response
from flask.ext import restful
from flask_login import login_required, LoginManager

import voluptuous

_logger = logging.getLogger(__name__)

import geocode.geocode_main

from geocode.web.geocodeUsers import request_user


class InvalidRequestException(Exception):
    '''Invalid Request exception.'''
    pass


def create_app(userdb, **kwargs):
    '''
    This method instantiates the RESTful web service app
    and returns it.

    Production mode: called from the .wsgi file.
    Standalone mode: used by developers to do local service testing
    '''

    app = Flask(__name__)
    api = restful.Api(app)

    api.add_resource(RootHandler, '/')
    api.add_resource(GeocodeService, '/geocoder/')
    if hasattr(app, 'api'):
        errmsg = 'app already has api attribute'
        _logger.error(errmsg)
        raise Exception(errmsg)
    else:
        app.api = api
    _logger.debug('returning app')

    # configure app to use specified user db and app secret key
    # ( required for flask-login module)
    app.config['userdb'] = userdb
    app.secret_key = "\xa9\xb6\xbb\xa9;XF>\x7fHd-@z!|\x7f\xa7'V\x1c6K\xe6"

    # use login manager to manage api requests
    # set request_user method as login manager's request loader (will be called
    # when a method is decorated with @login_required
    login_manager = LoginManager()
    login_manager.request_loader(request_user)
    login_manager.init_app(app)

    return app


def Coerce(input_type, msg=None):
    '''Coerce the type.'''

    def my_coerce(input_param):
        '''Coerce the given parameter.'''
        try:
            return input_type(input_param)
        except ValueError:
            raise Exception(msg or ('expected {0}'.format(input_type.__name__)))

    return my_coerce


class ServiceUtils(object):
    ''' Currently a container for request validation '''

    def __init__(self):
        pass


    def check_request(self, context):
        required_fields = ['street', 'city', 'state_prov', 'postal_code']
        keys_present = []
        # get all keys in the request, raise exception if key has an empty value
        for key, value in context.iteritems():
            keys_present.append(key)
            if key in required_fields and value is None:
                raise InvalidRequestException('Invalid Request')
        # invalid request if a required key isn't present in the request
        for required_key in required_fields:
            if required_key not in keys_present:
                raise InvalidRequestException('Invalid Request')

class GeocodeService(restful.Resource):
    __VERSION__ = 'v1'
    __SU = ServiceUtils()
    __REQUEST_SCHEMA = voluptuous.Schema({
        voluptuous.Required('street'): Coerce(str),
        voluptuous.Required('city'): Coerce(str),
        voluptuous.Required('state_prov'): Coerce(str),
        voluptuous.Required('postal_code'): Coerce(str),
        'country': Coerce(str),
        'key': Coerce(str),
        'geocoder': Coerce(str)
    })
    __DEFAULT_GEOCODERS = [geocode.geocode_main.ISO_ACCEPTANCE, geocode.geocode_main.GOOGLE_GEO]

    def __init__(self):
        pass

    def _responseWrapper(self):
        '''Prepare response'''

        return {'status': '', 'latitude': '-999.9', 'longitude': '-999.9', 'quality': '-99',
                'formatted_address': ''}

    def _internalError(self):
        _logger.error('An internal error is being thrown', exc_info=True)
        return make_response('An internal error has occurred.', 500)

    def _generateError(self, error_code):
        return make_response("ERROR", error_code, {'Content-Type': 'application/json'})


    # construct a dictionary of address components from response
    def _geocodedAddressFromResponse(self, response):

        return {'street': response['street'], 'city': response['city'], 'state_prov': response['state_prov'],
                'postal_code': response['postal_code'], 'country': response['country']}

    # get requires API key authentication. login_required decorator takes care of that
    @login_required
    def get(self):
        '''Geocode request'''

        try:
            context = {
                'street': request.args.get('street'),
                'city': request.args.get('city'),
                'state_prov': request.args.get('state_prov'),
                'postal_code': request.args.get('postal_code'),
                'country': request.args.get('country'),
                'geocoder': request.args.get('geocoder'),
            }

            # check to see if request is valid
            GeocodeService.__SU.check_request(context)

            context = self.__REQUEST_SCHEMA(context)

        # after checking context, if request is invalid an InvalidRequestException will be thrown
        except InvalidRequestException as ex:
            _logger.error('Invalid context: %s.', ex)
            return make_response("Invalid request: {0}".format(str(ex)), 400, {'Content-Type': 'text/plain'})

        geocoders = GeocodeService.__DEFAULT_GEOCODERS
        response = geocode.geocode_main.geocode(
            context["street"], context["city"], context["state_prov"],
            context["postal_code"], geocoders)

        latitude = response['latitude']
        longitude = response['longitude']
        street = response['street']
        city = response['city']
        state_prov = response['state_prov']
        postal_code = response['postal_code']
        country = response['country']
        error_msgs = response['error_msg']

        _logger.debug("(%s, %s) :: %s" % (latitude, longitude, error_msgs))
        wrapper = self._responseWrapper()

        # if we have a latitude and longitude then geocode was successful
        # we return the expected fields, along with formatted address
        # and geocoded address (as returned by the geocoder response)
        # In this case the formatted address is taken directly from the
        # geocoder response and not the user request
        if latitude and longitude:
            wrapper["status"] = "OK"
            wrapper["quality"] = response['quality']
            wrapper["latitude"] = latitude
            wrapper["longitude"] = longitude
            wrapper["formatted_address"] = " ".join((street, city, state_prov, postal_code, country))
            wrapper["geocoded_address"] = self._geocodedAddressFromResponse(response)

        # if geocoder could not return longitude/latitude we indicate
        # the request was invalid and return the formatted address
        # as specified by the user request. We do not return the geocoded address
        else:
            wrapper["status"] = "INVALID_ADDR"
            wrapper["quality"] = 0
            wrapper["formatted_address"] = " ".join((context["street"], context["city"],
                                                     context["state_prov"], context["postal_code"]))

        code = 200
        return make_response(json.dumps(wrapper), code, {'Content-Type': 'application/json'})


class RootHandler(restful.Resource):
    '''Service handler.'''
    _INDEX = ''.join(pkg_resources.resource_stream('geocode', 'web/html/index.html').readlines())

    def __init__(self):
        pass

    def get(self):
        '''Get response.'''

        _logger.debug(RootHandler._INDEX)
        code = 200
        response = make_response(RootHandler._INDEX, code, {'Content-Type': 'text/html'})

        return response


if __name__ == '__main__':  # pragma: no cover

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='''Stand alone web-server version of geocodeService

Examples:

    (with default settings)
    geocodeService.py --hostconfig dev --port 24601 user.db

    (allow external connections to the standalone server)
    geocodeService.py --hostconfig toExternal

After activation, queries can be made with the following syntax:
http://127.0.0.1:<port>/geocoder/?<parameters>

e.g., http://localhost:24602/geocoder/?city=Lexington&country=USA&street=131%20Hartwell%20Ave&postal_code=02421&key=testing&state_prov=MA
        ''')

    parser.add_argument('-p', '--port', default=24602, dest='port',
                        type=int, help='Port on which to run.')
    parser.add_argument('-l', '--logconfig', default='dev_logging.cfg', dest='log_config',
                        help='Logging configuration file.')
    parser.add_argument('--hostconfig', default='dev', dest='hostconfig',
                        help='flag for external visibility of the standalone web service (dev|toExternal)')
    parser.add_argument("userdb", help="userdb filename")

    args = parser.parse_args()

    cfg_stream = pkg_resources.resource_stream('geocode', args.log_config)
    logging.config.fileConfig(cfg_stream, disable_existing_loggers=False)

    hostcfg = '127.0.0.1'
    if args.hostconfig == 'toExternal':
        hostcfg = '0.0.0.0'

    app = create_app(args.userdb)
    app.logger.debug("Use user database: " + args.userdb)

    app.logger.debug("run app with " + args.log_config)
    app.run(debug=True, port=args.port, host=hostcfg)
