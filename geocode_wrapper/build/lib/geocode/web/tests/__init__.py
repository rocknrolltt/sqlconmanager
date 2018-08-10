#!/bin/env python

# @package geocode.web.tests.__init__
#
# @brief
#
# geocoder wrapper web service unit tests
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
# None
#
# CONTACT:
#
# Atmospheric & Environmental Research, Inc.
#   131 Hartwell Ave.
#   Lexington, MA 02421-3126 USA
#   Phone: 781.761.2288
#
# @author Mike Sze: msze@aer.com
#

import unittest
import logging
import json

import geocode
import geocode.web
import geocode.web.geocodeService


class GeocodeWebUnitTests(unittest.TestCase):
    '''Test the Geocoder Flask Web Service.'''

    def setUp(self):
        self.app = geocode.web.geocodeService.create_app('user.db').test_client()
        pass

    def sampleParameters(self):
        context = {'street': '131 Hartwell Ave',
                   'city': 'Lexington',
                   'state_prov': 'MA',
                   'postal_code': '02421',
                   'country': 'USA',
                   'key': '32aab59a-0482-4950-b3a5-8caaec18235c'}

        return context

    def sampleGeocodedAddress(self):
        sample = {"street": "131 Hartwell Ave", "city": "Lexington", "state_prov": "MA", "postal_code": "02421",
                  "country": "US"}

        return sample

    def test_index(self):
        rv = self.app.get("/")
        self.assertEquals(200, rv.status_code)

    def test_valid_get(self):
        context = self.sampleParameters()
        url = self.buildGet("/geocoder/", context)
        rv = self.app.get(url)

        self.assertEquals(200, rv.status_code)

        expected = json.loads('{"status":"OK", "latitude":"42.4629", '
                              '"formatted_address":"131 Hartwell Ave Lexington MA 02421 US", '
                              '"quality": 1, "longitude": "-71.2676"}')

        actual = json.loads(rv.data)

        # first test if geocoded_address is as expected
        self.assertTrue(abs(float(expected["latitude"]) - float(actual[u'latitude'])) < 0.0005)
        self.assertTrue(abs(float(expected["longitude"]) - float(actual[u'longitude'])) < 0.0005)
        self.assertTrue(actual[u'quality'] >= 1)


    def buildGet(self, endpoint, dictionary):
        params = []
        for k, v in dictionary.iteritems():
            params.append('%s=%s' % (k, v))
        url = '%s?%s' % (endpoint, '&'.join(params))

        return url

    def testAuthentication(self):
        context = self.sampleParameters()
        context['key'] = 'incorrect'

        url = self.buildGet("/geocoder/", context)
        rv = self.app.get(url)

        self.assertEquals(401, rv.status_code)

        context['key'] = '32aab59a-0482-4950-b3a5-8caaec18235c'
        url = self.buildGet("/geocoder/", context)
        rv = self.app.get(url)
        self.assertEquals(200, rv.status_code)

    def testInvalidGet(self):
        invalid_context = {'key': '32aab59a-0482-4950-b3a5-8caaec18235c'}

        url = self.buildGet("/geocoder/", invalid_context)
        rv = self.app.get(url)

        # error code 400 indicates Bad Request
        self.assertEquals(400, rv.status_code)

        # test one missing param
        one_missing = {'street': '131 Hartwell Ave',
                       'city': 'Lexington',
                       'postal_code': '02421',
                       'country': 'USA',
                       'key': '32aab59a-0482-4950-b3a5-8caaec18235c'}

        url = self.buildGet("/geocoder/", one_missing)
        rv = self.app.get(url)
        self.assertEquals(400, rv.status_code)

    def testInvalidAddress(self):
        context = self.sampleParameters()
        context['city'] = 'Whoville'
        context['street'] = '1 Horton Way'

        url = self.buildGet("/geocoder/", context)
        rv = self.app.get(url)

        self.assertEquals(200, rv.status_code)

        expected = json.loads(
            '{"status": "INVALID_ADDR", "latitude": "-999.9", "formatted_address": "1 Horton Way Whoville MA 02421", '
            '"quality": 0, "longitude": "-999.9"}')

        actual = json.loads(rv.data)

        self.assertTrue(sorted(expected.items()) == sorted(actual.items()))



if __name__ == '__main__':
    unittest.main()
