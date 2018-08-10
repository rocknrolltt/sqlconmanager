import logging
import pkg_resources
import geocode.web.geocodeService

# Very important that the object is called 'application'
config_file = pkg_resources.resource_stream('geocode', 'logging.cfg')
logging.config.fileConfig(config_file, disable_existing_loggers=False)
application = geocode.web.geocodeService.create_app()
