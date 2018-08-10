from setuptools import setup

INSTALL_REQUIRES = [
    "geopy>=0.99",
    'us',
    'nose>=1.0',
    'requests>=1.2.2',
    'dateutils>=0.6.6',
    'Flask==0.10',
    'Flask-RESTful>0.2.2',
    'voluptuous>=0.8.4',
    'Flask-Login',
]
TESTS_REQUIRES = [
    'nose-cov',
    'pylint',
    'tox'
]

version = "0.4"  # pylint: disable=C0103

setup(
    name='geocode',
    version=version,
    description='Geocoder for TSD',
    author='AER',
    author_email='msze@aer.com',
    packages=['geocode', 'geocode.web', 'geocode.web.tests', 'geocode.tests'],
    scripts=['scripts/benchmark_geocoder.wsgi', 'geocode/web/geocodeService.py', 'geocode/web/setup_user_db.py'],
    install_requires=INSTALL_REQUIRES,
    setup_requires=['nose>=1.0', 'coverage'],
    # tests_require=TESTS_REQUIRES,
    test_suite='nose.collector',
    package_data={"geocode": ['resources/iso_geoloc_req_a.xml',
                              'resources/iso_geoloc_req_p.xml',
                              'web/html/index.html',
                              'logging.cfg',
                              'dev_logging.cfg',
                              'web/user.db']},
    # Bypass zipping on build/install process to avoid
    # zip-cache bugs on NFS filesystems.
    zip_safe=False,
)
