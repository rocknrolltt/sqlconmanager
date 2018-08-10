#!/usr/bin/env python
'''ISO geolocation functions.'''

from urllib import urlencode
import urllib2
import xml.dom.minidom
import pkg_resources
import logging

# Define time-out for the ISO geolocation service.
ISO_GEOLOC_TIMEOUT_SEC = 10

# ISO geolocation web sites.
# 'P' is for production, while 'A' is for acceptance / testing.
ISO_URL = {'P': r'https://passport.iso.com/PPWebListener/HTTPRequestListener',
           'A': r'https://passportu.iso.com/PPWebListener/HTTPRequestListener'}

# defaul country for iso geocoder is usa
COUNTRY = 'US'


class IsoGeolocation(object):
    '''Geocoder using the ISO API.'''

    def __init__(self, system):
        '''Initialization - open the request XML file.'''

        self.password = None
        self.response = None
        self.user = None
        self.system = system
        infile = None
        if system == 'A':
            infile = 'iso_geoloc_req_a.xml'
        elif system == 'P':
            infile = 'iso_geoloc_req_p.xml'

        # Open resource file located in resources
        with pkg_resources.resource_stream('geocode', 'resources/' + infile) as ifile:
            llines = ifile.readlines()
        self.template = llines[0].strip()

    def url(self):
        '''Return ISO geolocation URL.'''
        return ISO_URL[self.system]

    def geocode(self, address):
        '''Replace the address fields in the XML template with the given
        address fields; call geocoder.'''

        outxml = self.template
        cust_perm_id_1 = outxml.index("<CustPermId>") + len("<CustPermId>")
        cust_perm_id_2 = outxml.index("</CustPermId>")
        self.user = outxml[cust_perm_id_1:cust_perm_id_2]
        passwd_1 = outxml.index("<Pswd>") + len("<Pswd>")
        passwd_2 = outxml.index("</Pswd>")
        self.password = outxml[passwd_1:passwd_2]
        outxml = outxml.replace('STREET', address[0])
        outxml = outxml.replace('CITYNAME', address[1])
        outxml = outxml.replace('STATEABBR', address[2])
        outxml = outxml.replace('ZIPCODE', address[3])
        params = {'reqData': "%s" % outxml, 'RequestHeaders': "", 'Connection': 'keep-alive', 'Accept-Charset': 'utf-8'}

        #logging.getLogger(__name__).debug("request_xml: %s", outxml)

        url = self.url()
        params = urlencode(params)


        return self.geocode_url(url, params)

    def geocode_url(self, url, params):
        '''Get the appropriate login / password; send the web services request
        to the specified URL.'''

        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, url, self.user, self.password)

        auth_handler = urllib2.HTTPBasicAuthHandler(password_mgr)
        opener = urllib2.build_opener(auth_handler)
        urllib2.install_opener(opener)

        self.response = urllib2.urlopen(url, params, ISO_GEOLOC_TIMEOUT_SEC)
        page = self.response.read()
        return parse_geocode_xml(page)


def parse_geocode_xml(page):
    '''Parse the location name, latitude, and longitude from the given XML
    response.'''

    doc = xml.dom.minidom.parseString(page)

    #logging.getLogger(__name__).debug("parsed iso geocoder: %s", doc.toprettyxml())

    response = response_components()
    status = None
    status_nodes = doc.getElementsByTagName('StatusDesc')

    # check if any status nodes indicate 'Failed'
    # This means the geocoding was not successful and we return an error_msg
    for node in status_nodes:
        status = get_node_value(node)

    if status == 'FAILED':
        error_node = doc.getElementsByTagName('ErrorMsg')[0]
        response['error_msg'] = get_node_value(error_node)
        logging.getLogger(__name__).debug("returning something with an error! %s", get_node_value(error_node))

        return response

    node = doc.getElementsByTagName('HomeLatitude')[0]
    lat = get_node_value(node)
    node = doc.getElementsByTagName('HomeLongitude')[0]
    lon = get_node_value(node)
    node = doc.getElementsByTagName('MatchType')[0]
    match = get_node_value(node)

    # check for geocoding not coming up with a match
    if lat == '' or lon == '' or match == '':
        match = 'F'
        lat = None
        lon = None

    node = doc.getElementsByTagName('HomeStreetNum')[0]
    number = get_node_value(node)
    node = doc.getElementsByTagName('HomeStreetName')[0]
    street = get_node_value(node)
    node = doc.getElementsByTagName('HomeStreetType')[0]
    street_type = get_node_value(node)
    node = doc.getElementsByTagName('HomeCity')[0]
    city = get_node_value(node)
    node = doc.getElementsByTagName('HomeState')[0]
    state = get_node_value(node)
    node = doc.getElementsByTagName('HomeZip')[0]
    zip_code = get_node_value(node)

    street = number + ' ' + street + ' ' + street_type

    response['match'] = match
    response['latitude'] = lat
    response['longitude'] = lon
    response['street'] = street.title()
    response['city'] = city.title()
    response['state_prov'] = state
    response['postal_code'] = zip_code
    response['country'] = COUNTRY

    logging.getLogger(__name__).debug("iso_geoloc.py ::: %s", response)
    return response


def get_node_value(node):
    '''Get the node value (first child value).'''

    if node.firstChild is None:
        return ""
    else:
        return node.firstChild.nodeValue.strip()


def response_components():
    '''Container for geocoder response. Response is a dictionary '''

    return {'latitude': None, 'longitude': None, 'street': None,
            'city': None, 'state_prov': None,
            'postal_code': None, 'country': None,
            'error_msg': None, 'quality': None}


if __name__ == '__main__':
    # Use the acceptance (testing) ISO geolocation web site.
    geolocation = IsoGeolocation('A')
    input_address = ['307 East Main Street', 'New York City', 'NY', '73069']
    output_lat_lon = geolocation.geocode(input_address)
    print output_lat_lon
