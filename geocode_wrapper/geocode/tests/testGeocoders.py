'''Unit tests for geocode module.'''

import re
import logging
import unittest

import nose

from geocode import geocode_main as main


def get_ambiguous_address():
    return {'street': '100 Washington Street',
            'city': 'Boston',
            'state': 'MA',
            'postal': '90210'}

def get_address():
    return {'street': '131 Hartwell Ave',
            'city': 'Lexington',
            'state': 'MA',
            'postal': '02421'}


def get_us_unicode_address():
    return {'street': '17 Kauiki St',
            'city': 'Hana',
            'state': 'HI',
            'postal': '96713'}


class TestGeocoders(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        pass

    @classmethod
    def teardown_class(cls):
        pass

    def get_montreal_address(self):
        return dict(street='845 Rue Sherbrooke Ouest', city='Montreal', state='QC', postal='H3A0G4')


    def test_canada_geocoder(self):
        '''Test of geocoding Canadian address.'''

        address = self.get_montreal_address()

        # test if successful geocode returns as expected
        expected = {'city': u'Montr\xe9al', 'street': u'845 Rue Sherbrooke Ouest', 'postal_code': u'H3A 2T5',
                    'match': 'A', 'country': u'CA', 'latitude': '45.5061666',
                    'state_prov': u'QC', 'error_msg': None, 'longitude': '-73.5776415'}

        test_geocoder_name = main.GOOGLE_GEO

        actual = main.geocode(address['street'], address['city'], address['state'], address['postal'],
                              geocoder=test_geocoder_name, country='CAN')

        # expecting an exact match here
        assert not actual['error_msg']
        assert TestGeocoders.compare_geocode_results(expected, actual)

        address = {"city" : "Evansville",
                   "country" : "CAN",
                   "postal_code" : "T8T 1Z7",
                   "state" : "AB",
                   "street" : "70020 SAINT THOMAS CT"}

        actual = main.geocode(address['street'], address['city'], address['state'], address['postal_code'],
                              geocoder=test_geocoder_name, country='CAN')
        assert actual['error_msg']


    def test_iso_geocoder(self):

        address = get_address()

        # test if successful geocode returns as expected
        expected = {'city': 'Lexington', 'street': '131 Hartwell Ave', 'postal_code': u'02421',
                    'match': 'A', 'country': 'US', 'latitude': '42.462799',
                    'state_prov': 'MA', 'error_msg': None, 'longitude': '-71.267723'}

        test_geocoder_name = main.ISO_ACCEPTANCE

        actual = main.iso_geocoder(test_geocoder_name, address['street'], address['city'], address['state'],
                                   address['postal'])

        # expecting an exact match here
        assert not actual['error_msg']
        assert TestGeocoders.compare_geocode_results(expected, actual)

        # change to ambiguous address and test if error is returned
        # check that lat and long is None and match is S instead of A or E
        address['street'] = '131 Lexington Ave'
        address['postal'] = '024210101010101'
        actual = main.iso_geocoder(test_geocoder_name, address['street'], address['city'], address['state'],
                                   address['postal'])
        logging.getLogger(__name__).debug("actual geocoder response: %s", actual)
        error_msg = actual['error_msg']
        latitude = actual['latitude']
        longitude = actual['longitude']

        assert not latitude and not longitude and error_msg
        logging.getLogger(__name__).debug("error message: %s", error_msg)
        assert re.search('Geocoder match is not of sufficient quality', error_msg)
        assert actual['postal_code'] == '02421'

        # check that invalid argument error is being returned
        # state has an invalid length, so Input error should be returned
        # all the values except error_msg should be None
        address['state'] = 'AAL'
        logging.getLogger(__name__).debug("testing invalid state results: %s", address['state'])
        actual = main.iso_geocoder(test_geocoder_name, address['street'], address['city'], address['state'],
                                   address['postal'])

        logging.getLogger(__name__).debug("invalid state results: %s", actual)
        assert actual['error_msg'] == 'ISO geocoder timed out or otherwise failed.'

        for key, value in actual.iteritems():
            if key is not 'error_msg':
                assert value is None

    def test_min_geocoder_quality(self):
        '''Testing minimum geocoding quality option by making a request to a known RANGE_INTERPOLATED
        input address and then re-requesting with minimum requirement for ROOFTOP.'''

        address = {'street': '300 Hartwell Ave',
                   'city': 'Lexington',
                   'state': 'MA',
                   'postal': '02421'}

        # test if successful geocode returns as expected
        expected = {'city': 'Lexington', 'street': '300 Hartwell Avenue', 'postal_code': '02421',
                    'country': 'US', 'latitude': '42.4623533', 'state_prov': 'MA', 'quality': 60,
                    'error_msg': None, 'longitude': '-71.2657524'}

        test_geocoders = [main.ISO_ACCEPTANCE, main.GOOGLE_GEO]
        logging.getLogger(__name__).debug("Testing default RANGE_INTERPOLATED")
        actual = main.geocode(address['street'], address['city'], address['state'], address['postal'],
                              geocoder=test_geocoders, min_quality=main.QUALITY_RANGE_INTERPOLATED)
        logging.getLogger(__name__).debug(actual)

        # this should match since Google does a RANGE INTERPOLATION even though 300 Hartwell Ave
        # doesn't exist.
        self.assertIsNone(actual['error_msg'])
        assert TestGeocoders.compare_geocode_results(expected, actual)

        actual = main.geocode(address['street'], address['city'], address['state'], address['postal'],
                              geocoder=test_geocoders, min_quality=main.QUALITY_ROOFTOP)
        logging.getLogger(__name__).debug("Testing stricter ROOFTOP")

        # this should fail since neither geocoder can match ROOFTOP

        # insufficient ISO geocoder match
        assert re.search(r'Geocoder match is not of sufficient quality \(70\); was instead: Z/10.',
                         actual['error_msg'])

        # insufficient Google match
        assert re.search(r'Geocoder match is not of sufficient quality \(70\); was instead: RANGE_INTERPOLATED/60.',
                         actual['error_msg'])

        canada_address = {'street': '51 Cave',
                          'city': 'Edmonton',
                          'state': 'AB',
                          'postal': 'T5J 3Z4',
                          'country': 'CAN'}
        # this address is actually pretty good now!
#         logging.getLogger(__name__).debug("here is the Canadian geocoder address..., query with min quality of %s",
#                                           main.QUALITY_APPROXIMATE)
#         actual = main.google_geocoder(canada_address['street'], canada_address['city'],
#                                       canada_address['state'], canada_address['postal'],
#                                       canada_address['country'], min_quality=main.QUALITY_APPROXIMATE)
#         logging.getLogger(__name__).debug("quality: %s", actual['quality'])
#         self.assertEquals(main.QUALITY_APPROXIMATE, actual['quality'])

        canada_address2 = {'street': '5005 46 street',
                           'city': 'Valleyview',
                           'state': 'AB',
                           'postal': 'T0H 3N0',
                           'country': 'CAN'}

        logging.getLogger(__name__).debug("here is the Canadian geocoder address 2..., query with min quality of %s",
                                          main.QUALITY_APPROXIMATE)
        actual = main.google_geocoder(canada_address2['street'], canada_address2['city'],
                                      canada_address2['state'], canada_address2['postal'],
                                      canada_address2['country'], min_quality=main.QUALITY_APPROXIMATE)
        self.assertEquals(main.QUALITY_RANGE_INTERPOLATED, actual['quality'])
        self.assertEquals(canada_address2['postal'], actual['postal_code'])


    def test_google_geocoder(self):

        address = get_address()

        # test valid address return
        expected = {'city': 'Lexington', 'street': '131 Hartwell Avenue', 'postal_code': '02421',
                    'country': 'US', 'latitude': '42.4624917',
                    'state_prov': 'MA', 'error_msg': None, 'longitude': '-71.2679953'}

        actual = main.google_geocoder(address['street'], address['city'], address['state'],
                                      address['postal'])
        assert TestGeocoders.compare_geocode_results(expected, actual)

        # test inaccurate match return
        address['street'] = 'Hartwell Avenue'
        actual = main.google_geocoder(address['street'], address['city'], address['state'],
                                      address['postal'])

        assert not actual['latitude'] and not actual['longitude']
        assert re.search('Geocoder match is not of sufficient quality', actual['error_msg'])

        # so it looks like Google can resolve this (throwing out the bad zip code)
        if False:
            amb_address = get_ambiguous_address()
            actual = main.google_geocoder(amb_address['street'], amb_address['city'], amb_address['state'],
                                          amb_address['postal'])
            assert not actual['latitude'] and not actual['longitude']
            assert actual['error_msg'] == 'Google geocoder match is not ROOFTOP; was instead: RANGE_INTERPOLATED.'

        # test invalid address return
        address['street'] = 'nonsense'
        address['state'] = 'CALP'
        address['postal'] = '0202020202'

        actual = main.google_geocoder(address['street'], address['city'], address['state'],
                                      address['postal'])
        assert not actual['latitude'] and not actual['longitude']
        assert actual['error_msg'] == 'Google could not geocode address. Zero results returned'


        # this address actually works now! so not failing any more. This isn't a useful test.
        canada_address = {'street': '51 Cave',
                          'city': 'Edmonton',
                          'state': 'AB',
                          'postal': 'T5J 3Z4',
                          'country': 'CAN'}

#         logging.getLogger(__name__).debug("here is the Canadian geocoder address....")
#         actual = main.google_geocoder(canada_address['street'], canada_address['city'], canada_address['state'],
#                                       canada_address['postal'], canada_address['country'])
# 
#         logging.getLogger(__name__).debug(actual)
#         assert not actual['latitude'] and not actual['longitude']

    @unittest.skip("We do not have a valid Bing license at this time...")
    def test_bing_geocoder(self):
        address = get_address()

        # test valid address return
        expected = {'city': 'Lexington', 'street': '131 Hartwell Ave', 'postal_code': '02421',
                    'country': 'United States', 'latitude': '42.462799',
                    'state_prov': 'MA', 'error_msg': None, 'longitude': '-71.267723'}

        actual = main.bing_geocoder(address['street'], address['city'], address['state'],
                                    address['postal'])
        assert TestGeocoders.compare_geocode_results(expected, actual) == True

        # test return with multiple match codes -- indicates geocoder could not
        # match all information and went 'Up Hierarchy'
        address['street'] = 'This street does not exist'
        actual = main.bing_geocoder(address['street'], address['city'], address['state'],
                                    address['postal'])
        assert not actual['latitude'] and not actual['longitude']
        assert actual['error_msg'] == 'Bing geocoder - 2 match codes - invalid.'

        # test return of ambiguous address -- this address can have multiple boston
        # locations, so we should be getting an inaccurate match
        # bing however returns an accurate match -- unreliable
        amb_address = get_ambiguous_address()
        actual = main.bing_geocoder(amb_address['street'], amb_address['city'], amb_address['state'],
                                    amb_address['postal'])
        # assert not actual['latitude'] and not actual['longitude']
        # assert actual['error_msg'] == 'Bing geocoder - 2 match codes - invalid.'

        # test invalid return (without street field)
        address['street'] = ''
        actual = main.bing_geocoder(address['street'], address['city'], address['state'],
                                    address['postal'])
        assert not actual['latitude'] and not actual['longitude']
        assert actual['error_msg'] == 'Bing geocoder timed out or otherwise failed.'

        # test invalid address return
        address['street'] = 'nonsense'
        address['state'] = 'CALP'
        address['postal'] = '0202020202'

        actual = main.bing_geocoder(address['street'], address['city'], address['state'],
                                    address['postal'])
        assert not actual['latitude'] and not actual['longitude']
        assert actual['error_msg'] == 'Bing could not geocode address. Zero results returned'

    def test_unicode_addresses(self):
        google_mtl_expected = {'city': 'Montreal', 'street': '845 Rue Sherbrooke Ouest', 'postal_code': 'H3A 2T5',
                               'country': 'CA', 'latitude': '45.5061666',
                               'state_prov': 'QC', 'error_msg': None, 'longitude': '-73.5776415'}

        bing_mtl_expected = {'city': 'Montreal', 'street': '845 Rue Sherbrooke O', 'postal_code': 'H3A 2T5',
                             'country': 'Canada', 'latitude': '45.5036697',
                             'state_prov': 'QC', 'error_msg': None, 'longitude': '-73.5749588'}

        iso_expected = {'city': 'Hana', 'street': '17 Kauiki St', 'postal_code': '96713',
                        'match': 'A', 'country': 'US', 'latitude': '20.757821',
                        'state_prov': 'HI', 'error_msg': None, 'longitude': '-155.990085974'}

        # ISO Unicode
        unicode_address = get_us_unicode_address()
        actual = main.iso_geocoder(main.ISO_ACCEPTANCE, unicode_address['street'], unicode_address['city'],
                                   unicode_address['state'], unicode_address['postal'])
        print actual

        # GOOGLE Unicode
        mtl_address = get_us_unicode_address()
        actual = main.google_geocoder(mtl_address['street'], mtl_address['city'], mtl_address['state'],
                                      mtl_address['postal'])
        print actual
        # assert cmp(mtl_expected,actual) == 0

        # BING Unicode
        actual = main.bing_geocoder(mtl_address['street'], mtl_address['city'], mtl_address['state'],
                                    mtl_address['postal'])
        print actual

        # assert cmp(bing_mtl_expected,actual) == 0

    @staticmethod
    def compare_geocode_results(expected_geocode, test_geocode):
        # 4th digit: 40ft
        # 5th digit:  4ft

        epsilon = 0.0002
        isEqual = True
        for name in ['city', 'street', 'postal_code', 'country', 'state_prov', 'error_msg']:
            if expected_geocode[name] != test_geocode[name]:
                logging.debug("%s did not match! %s cmp %s", name, expected_geocode[name], test_geocode[name])
                isEqual = False

        for coord in ['latitude', 'longitude']:
            if test_geocode[coord] is None:
                logging.debug('test %s is None', coord)
            elif expected_geocode[coord] != test_geocode[coord]:
                difference = abs(float(expected_geocode[coord]) - float(test_geocode[coord]))

                if difference > epsilon:
                    logging.debug('coordinate %s did not match! %s cmp %s',
                                  coord, expected_geocode[coord], test_geocode[coord])
                    isEqual = False
                else:
                    logging.debug('coordinate %s differ at 5th decimal place! %s cmp %s',
                                  coord, expected_geocode[coord], test_geocode[coord])
        return isEqual

if __name__ == '__main__':
    nose.main()
