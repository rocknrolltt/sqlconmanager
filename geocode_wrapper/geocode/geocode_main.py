#!/usr/bin/env python
'''Benchmark Transactional Services [BTS] geocoding.'''

import logging
import us
import collections
from geopy.geocoders import googlev3, Bing
from geocode.iso_geoloc import IsoGeolocation, response_components

# Geocoders.
ISO_PRODUCTION = 101
ISO_ACCEPTANCE = 102
GOOGLE_GEO = 103
BING_GEO = 104

QUALITY_ROOFTOP = 70
QUALITY_RANGE_INTERPOLATED = 60
QUALITY_GEOMETRIC_CENTER = 30
QUALITY_APPROXIMATE = 10

GOOGLE_QUALITY_MAP = {'ROOFTOP': QUALITY_ROOFTOP,
                      'RANGE_INTERPOLATED': QUALITY_RANGE_INTERPOLATED,
                      'GEOMETRIC_CENTER': QUALITY_GEOMETRIC_CENTER,
                      'APPROXIMATE': QUALITY_APPROXIMATE}

# If the ISO geocoder match type is "A" (matches parcel data), then we
# can have some confidence that the geocoding is fairly accurate and we
# can proceed.  If the geocode match type is "E" (interpolated address
# match), the geocoding is probably reasonably accurate.  If the match
# type is not "A" or not "E", try the back-up geocoder.
ISO_QUALITY_MAP = {'A': QUALITY_ROOFTOP,
                   'E': QUALITY_RANGE_INTERPOLATED,
                   'S': QUALITY_GEOMETRIC_CENTER,
                   'Z': QUALITY_APPROXIMATE}

def geocode(street, city, state_prov, postal_code,
            geocoder=None, country='US', min_quality=QUALITY_RANGE_INTERPOLATED):
    '''Geocode the given address using configured geocoder service and other parameters.

    Args:
        street (str): REQUIRED. street number and street name
        city (str): REQUIRED.
        state_prov (str): REQUIRED. 2-letter State or Province code
        postal_code (str): REQUIRED.
        geocoder (list or enumerated Geocoder code): default is ISO_PRODUCTION
        country (str): default 'US'
        min_quality (enumerated quality threshold): default is QUALITY_RANGE_INTERPOLATED
    '''

    # If an unknown geocoder is given, use the ISO production geocoder as the primary geocoder.

    # parameter order is a little funny -- but it was to preserve backwards
    # compatibility
    use_geocoders = []

    # If no geocoder is provided, use the ISO production geocoder (only).
    if geocoder is None:
        use_geocoders.append(ISO_PRODUCTION)

    elif isinstance(geocoder, collections.Iterable):

        for geoc in geocoder:

            if geoc not in [ISO_PRODUCTION, ISO_ACCEPTANCE, GOOGLE_GEO, BING_GEO]:
                logging.getLogger(__name__).warn('geocode - given geocoder %s is not known.', geoc)
            else:
                use_geocoders.append(geoc)

        # Make sure there is at least one geocoder to use.
        if not use_geocoders:
            use_geocoders.append(ISO_PRODUCTION)

    elif geocoder in [ISO_PRODUCTION, ISO_ACCEPTANCE, GOOGLE_GEO, BING_GEO]:
        use_geocoders.append(geocoder)
    else:
        logging.getLogger(__name__).warn('geocode - given geocoder %s is not known; use ISO '
                                         'production geocoder instead.', geocoder)
        use_geocoders.append(ISO_PRODUCTION)

    # If the postal code has a leading 0 (such as for a New England ZIP code),
    # ensure that the leading zero
    # is not left off - for U.S. addresses only.
    if is_us50_state(state_prov):
        postal_code = str(postal_code).zfill(5)

    # Try to geocode the given address using the given geocoders in order
    # (there may be only one).
    error_msgs = ''
    response = None

    for geocoder in use_geocoders:

        if geocoder in [ISO_PRODUCTION, ISO_ACCEPTANCE]:
            # if ISO is the primary geocoder, we are more strict on the min_quality
            # (and more relaxed on the secondary geocoders)
            if geocoder == use_geocoders[0] and min_quality < QUALITY_RANGE_INTERPOLATED:
                iso_min_quality = QUALITY_RANGE_INTERPOLATED
            else:
                iso_min_quality = min_quality

            response = iso_geocoder(geocoder, street,
                                    city, state_prov,
                                    postal_code, country, iso_min_quality)

        elif geocoder == GOOGLE_GEO:
            response = google_geocoder(street,
                                       city, state_prov,
                                       postal_code, country, min_quality)

        elif geocoder == BING_GEO:
            response = bing_geocoder(street,
                                     city, state_prov,
                                     postal_code, country, min_quality)

        latitude = response['latitude']
        longitude = response['longitude']
        error = response['error_msg']

        if latitude and longitude:
            # We have a Lat and Lon and are ready to return from this function.
            logging.getLogger(__name__).debug("successful geocoding (using geocoder %s): %s %s",
                                              geocoder, latitude, longitude)
            break
        elif error:
            # The geocoder failed.  Try the next one if there is a next one.
            # Add two spaces between successive error messages for readability.
            logging.getLogger(__name__).warn("%s geocoder failed.... %s", geocoder, response['error_msg'])
            geocoder_of_record_string = "[geocoder_of_record %s]" % geocoder
            new_error_msg = geocoder_of_record_string + " " + response['error_msg']
            error_msgs += new_error_msg + '  '
            response['error_msg'] = error_msgs
        else:
            new_error_msg = 'All geocoders failed'
            error_msgs += new_error_msg + '  '
            response['error_msg'] = error_msgs

    return response


def iso_geocoder(geocoder, street, city, state_prov, postal_code,
                 country='US', min_quality=QUALITY_RANGE_INTERPOLATED):
    '''Call the ISO production or ISO acceptance geocoder to get the address's
    Lat / Lon.'''
    if country != 'US':
        logging.getLogger(__name__).warn("The ISO geocoder does not support any region other than US! (%s)",
                                         country)

    # The interface to the ISO geoocoders (both production and acceptance /
    # test) requires that the address components be in a list.
    geocoder_address = [street, city, state_prov, postal_code]

    # Assume that we are using the ISO production geocoder.
    geocoder_type = 'P'

    # Change the geocoder type if specified.
    if geocoder == ISO_ACCEPTANCE:
        geocoder_type = 'A'

    # Initialize the ISO geocoder class (prepare to call the geocoder).
    geocoder = IsoGeolocation(geocoder_type)

    # Call the ISO geocoder.  Note that the geocoder can time out and throw an
    # exception for various reasons (if the geocoder is down, if the geocoder
    # is very confused by the given address, etc.).
    try:
        response = geocoder.geocode(geocoder_address)

        # Log the ISO geocoder type to make sure that we are running the
        # correct version of the geocoder
        # (P for production / A for acceptance; testing).
        geocoder_type_msg = 'ISO Geocoder type: {0}'.format(geocoder_type)
        logging.info("message: %s", geocoder_type_msg)

        # Check if geocoder returned with an error and fail message
        # if error message is present in response, geocoding was unsuccessful
        # so we return. Otherwise there was a successful geocode query
        if response['error_msg']:
            logging.info("ISO geocoder (%s) error: %s", geocoder_type, response['error_msg'])
            return response

        if response['match'] in ISO_QUALITY_MAP and ISO_QUALITY_MAP[response['match']] >= min_quality:
            response['quality'] = ISO_QUALITY_MAP[response['match']]
        else:
            response['latitude'] = None
            response['longitude'] = None

            # Get the ISO geocoder match type for the error message (and for
            # logging).
            error_msg = 'Geocoder match is not of sufficient quality ({0}); was instead: ' \
                        '{1}/{2}.'.format(min_quality, response['match'], ISO_QUALITY_MAP[response['match']])
            logging.error("ISO geocoder (%s) insufficent quality match: %s", geocoder_type, error_msg)
            response['error_msg'] = error_msg

    except BaseException as exc:

        # The error message is different for an exception (time-out, etc.)
        # than for an inaccurate match.
        logging.getLogger(__name__).error("ISO Geocoder Exception: %s", exc)
        logging.getLogger(__name__).exception(exc)
        error_msg = 'ISO geocoder timed out or otherwise failed.'
        logging.error(error_msg)
        logging.error(exc)
        response = response_components()
        response['error_msg'] = error_msg

    return response


def google_geocoder(street, city, state_prov, postal_code,
                    country=None, min_quality=QUALITY_RANGE_INTERPOLATED):
    '''Call the Google geocoder to get the address's Lat / Lon.'''

    response = response_components()

    try_queries = []

    # Google requires the address to be in a comma-separated string.
    try_queries.append(', '.join([street, city, state_prov, postal_code]))
    region = None

    if country == 'CAN':
        try_queries.append(', '.join([street, city, state_prov]))
        region = 'CA'

    # Initialize the Google geocoder class (version 3) - prepare to call the
    # geocoder.
    geocoder = googlev3.GoogleV3()

    location = None
    for geocoder_address in try_queries:
        # Call the Google geocoder.  Note that the geocoder can time out and throw
        # an exception for various reasons (if the geocoder is down, if the
        # geocoder is very confused by the given address, etc.).
        try:
            logging.getLogger(__name__).debug("trying google geocoder with: %s", geocoder_address)
            location = geocoder.geocode(geocoder_address, True, region=region)

        except BaseException as exc:

            # The error message is different for an exception (time-out, etc.) than
            # for an inaccurate match.
            error_msg = 'Google geocoder timed out or otherwise failed.'
            logging.info(error_msg)
            logging.debug(exc)
            response['error_msg'] = error_msg

    # if location is None, then the geocoder did not return a match
    if not location:
        error = 'Google could not geocode address. Zero results returned'
        logging.getLogger(__name__).info(error)
        response['error_msg'] = error
        return response

    # The "raw" field in the return parameter from the geocoder contains
    # everything that we are interested in.
    location_raw = location.raw

    logging.getLogger(__name__).debug(location.raw)

    # Get the Google geocoder match type from the raw return.
    google_geo_match_type = location_raw['geometry']['location_type']

    quality_adjustment = 0

    # The google geocoder response has additional fields:
    # https://developers.google.com/maps/documentation/geocoding/intro#Results
    # 'partial_match' : this indicates that geocoding service was able to match with a
    #                   a portion of the address information (e.g., a match _ignoring_ the provided
    #                   city; there are other ways, too)
    # 'types' : is a list of the address types (e.g., street_address)
    #
    # in this case, the partial_match flag indicates some inconsistency between request and response
    # and _not_ an street_address.
    if 'partial_match' in location_raw and 'types' in location_raw:
        logging.getLogger(__name__).debug("types: %s", location_raw['types'])
        if 'street_address' not in location_raw['types']:
            quality_adjustment -= 20

    logging.getLogger(__name__).debug("GOOGLE geocode match type %s", google_geo_match_type)

    if google_geo_match_type in GOOGLE_QUALITY_MAP and \
       GOOGLE_QUALITY_MAP[google_geo_match_type] + quality_adjustment >= min_quality:

        response['latitude'] = str(location_raw['geometry']['location']['lat'])
        response['longitude'] = str(location_raw['geometry']['location']['lng'])
        address_components = location_raw['address_components']
        street_components = []

        # we need to return a canonical address response contained in the
        # address_components json object. Iterate through components
        # and assign them accordingly to our response object
        for component in address_components:
            types = component['types']
            component_name = component['long_name']

            # we can append street_components since they will be iterated through
            # in order (street number first, then route, etc)
            if 'street_number' in types:
                street_components.append(component_name)

            if 'route' in types:
                street_components.append(component_name)

            if 'locality' in types:
                response['city'] = component_name

            if 'administrative_area_level_1' in types:
                component_name = component['short_name']
                response['state_prov'] = component_name

            if 'country' in types:
                component_name = component['short_name']
                response['country'] = component_name

            if 'postal_code' in types:
                response['postal_code'] = component_name

        # now that Google Geocoder has some problems with Canadian geocoding with postal codes,
        # we need to insert in postal_code
        if 'postal_code' not in response or response['postal_code'] is None:
            response['postal_code'] = postal_code

        response['street'] = ' '.join(street_components)
        response['quality'] = GOOGLE_QUALITY_MAP[google_geo_match_type] + quality_adjustment
    else:

        # Provide the Google geocoder match type in the error message (and
        # for logging).
        error_msg = 'Geocoder match is not of sufficient quality ({0}); was instead: ' \
                    '{1}/{2}.'.format(min_quality, google_geo_match_type,
                                      GOOGLE_QUALITY_MAP[google_geo_match_type])
        logging.info(error_msg)
        response['error_msg'] = error_msg


    return response


# Note that as of 06/16/14, we are not using Bing for geocoding because we do
# not trust it - it has too many problems such as giving its highest accuracy
# / match values to an address that is a post office box.
def bing_geocoder(street, city, state_prov, postal_code,
                  country=None, min_quality=QUALITY_RANGE_INTERPOLATED):
    '''Call the Bing geocoder to get the address's Lat / Lon.'''

    if min_quality != QUALITY_RANGE_INTERPOLATED:
        logging.warn("Bing Geocoder has not yet implemented the min_quality threshold!")

    response = response_components()

    # Bing requires the address to be in a comma-separated string.
    geocoder_address = ','.join([street, city, state_prov, postal_code])

    # Initialize the Bing geocoder class using the Bing Map API key.
    geocoder = Bing('AgpUigcyyCn4A4ZJHo2lvXqt_4BrH0xr5wbGzfrcqgZUt6jaVG'
                    'vORIBM6SwqeEYd')

    # Call the Bing geocoder.  Note that the geocoder can time out for various
    # reasons (if the geocoder is down, if the geocoder is very confused by the
    # given address, etc.).
    try:
        location = geocoder.geocode(geocoder_address)

        # if location is None, then the geocoder did not return a match
        if not location:
            error = 'Bing could not geocode address. Zero results returned'
            logging.info(error)
            response['error_msg'] = error
            return response
        else:
            location = location.raw

        # Get the Bing geocoder match codes and confidence level from the raw
        # return.
        bing_geo_match_codes = location['matchCodes']
        bing_geo_conf_level = location['confidence']

        # The Bing geocoder match codes is always a list, even if there is only
        # one element.
        # In order for us to consider this match valid, there must be only one
        # element in the list.
        if len(bing_geo_match_codes) == 1:

            # Get the single match code from the match codes list.
            bing_geo_match_code = bing_geo_match_codes[0]

            # If the Bing geocoder match code is "Good" and the confidence is
            # "High", then in most cases we can have some confidence in the
            # accuracy of the geocoded coordinates, although Bing has returned
            # "Good" and "High" for an address that contains a post office box.
            if bing_geo_match_code == 'Good' and bing_geo_conf_level == 'High':
                latitude = location['point']['coordinates'][0]
                longitude = location['point']['coordinates'][1]

                if latitude and longitude:
                    response['latitude'] = str(latitude)
                    response['longitude'] = str(longitude)
                    response['street'] = location['address']['addressLine']
                    response['city'] = location['address']['locality']
                    response['state_prov'] = location['address']['adminDistrict']
                    response['postal_code'] = location['address']['postalCode']
                    response['country'] = location['address']['countryRegion']
                    response['quality'] = QUALITY_ROOFTOP

            else:

                # Provide the Bing geocoder match type in the error message
                # (and for logging).
                error_msg = 'Bing geocoder match is not Good / High; was ' \
                            'instead: {0} / {1}.'.format(bing_geo_match_code,
                                                         bing_geo_conf_level)
                logging.info(error_msg)
                response['error_msg'] = error_msg

        else:
            # Provide the Bing geocoder match count in the error message (and
            # for logging).
            error_msg = 'Bing geocoder - {0} match codes - ' \
                        'invalid.'.format(len(bing_geo_match_codes))
            logging.info(error_msg)
            response['error_msg'] = error_msg

    except:

        # The error message is different for an exception (time-out, etc.) than
        # for an inaccurate match.
        error_msg = 'Bing geocoder timed out or otherwise failed.'
        logging.info(error_msg)
        response['error_msg'] = error_msg
        response['latitude'] = None
        response['longitude'] = None

    return response


def is_us50_state(state):
    '''Is the given state (or province) one of the 50 states in the U.S.A. (or
    Washington, D.C.)?'''
    all_states = set([s.abbr for s in us.states.STATES])
    return state in all_states
