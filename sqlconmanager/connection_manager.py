#!/bin/env python
'''SQLSoup-based connection manager and unit tests.'''

import logging
import sqlsoup
import sqlalchemy
import yaml
import pkg_resources

logger = logging.getLogger(__name__)

#######################################################################################
# SQLSoup-based Connection manager and unit tests
#
# Putting all of our usernames and passwords (in plain text) in one file for easy
# access (by anyone and everyone!).

# If you get bored sometime, do some reading on the "Correct" way of implementing
# Enums in Python.
class ConnectionLevel:  # pylint: disable=C1001
    '''Connection level.'''

    # Dummy init function - to make pylint happy.
    def __init__(self):
        pass

    READ_ONLY = "ro"
    UPDATE = "update"
    ADMIN = "admin"


class ManagerConnectionException(Exception):
    pass


POOL_SIZE = 10
MAX_OVERFLOW = 10
DB_CONNECT_TIMEOUT = 30  # seconds
RECYCLE_CONNECTION_TIMEOUT = 1800  # seconds


class Manager(object):

    def __init__(self):
        self.config_stream = None
        self.database_configuration = "dev_test"
        self.database_echo = False
        self.db_engine = None
        self.db_configs = None

    def get_connection_config_list(self):
        ''' Return list of known DB connection configuration names.  Useful for iteration'''

        self._load_configs()

        return self.db_configs["database_configurations"].keys()

    def _load_configs(self):
        if self.db_configs is None:
            try:
                self.db_configs = yaml.load(self.config_stream)
                logger.debug('Successfully loaded supplied configuration yaml')
            except Exception as exc:
                # if config_stream is not set or is an invalid file, use the packaged dbconfig file
                logger.info('Loading packaged yaml')
                self.db_configs = yaml.load(pkg_resources.resource_stream('sqlconmanager', 'resources/dbconfig.yaml'))


    def get_engine(self, config_name=None, security_level=ConnectionLevel.READ_ONLY, force_flag=False):
        '''Get engine (engine is the home base for SQLAlchemy - a dialect and a connection pool.'''

        if self.db_engine is not None and force_flag is not True:
            logging.info('db engine already set, returning db engine')
            return self.db_engine

        if not config_name:
            config_name = self.database_configuration

        logger.info('Using configuration: {0}'.format(config_name))

        self._load_configs()

        try:
            logger.debug('Configuration: {0}'.format(self.db_configs))
            conn_config = self.db_configs['database_configurations'][config_name]
            (username, password) = conn_config['credentials'][security_level]
        except KeyError:
            logger.error('Unable to find the {0} credentials for "{1}")'.format(config_name, security_level))
            raise ManagerConnectionException('No credentials for {0}:{1}'.format(config_name, security_level))

        connstring = '{0}://{1}:{2}@{3}:{4}/{5}'.format(conn_config['dbtype'], username,
                                                        password,
                                                        conn_config["host"],
                                                        conn_config["port"],
                                                        conn_config["dbname"])

        logger.debug("Connection: {0}".format(connstring))

        self.db_engine = sqlalchemy.create_engine(connstring,
                                                  pool_size=POOL_SIZE,
                                                  max_overflow=MAX_OVERFLOW,
                                                  echo=self.database_echo, echo_pool=True,
                                                  pool_recycle=RECYCLE_CONNECTION_TIMEOUT)

        return self.db_engine

    def get_connection(self, config_stream, config=None, security_level=ConnectionLevel.READ_ONLY, sql_echo=False):
        '''Return the SQLSoup connection to the server/access level of your choice'''

        self.database_echo = sql_echo

        self.config_stream = config_stream
        logger.debug('Using config stream: {0}'.format(self.config_stream))
        an_engine = self.get_engine(config, security_level)

        is_valid_connection = False

        try:
            db = sqlsoup.SQLSoup(an_engine)
            is_valid_connection = self.validate_connection(db)
            logger.debug("Validating connection..isvalid: {0}".format(is_valid_connection))
        except Exception as e:
            logger.error("invalid connection, try reconnect of engine: {0}".format(e))
            an_engine = self.get_engine(config, security_level, force_flag=True)
            db = sqlsoup.SQLSoup(an_engine)

        if is_valid_connection is False:
            try:
                self.validate_connection(db)
            except Exception:
                logger.fatal("invalid connection, 2nd try")
                raise ManagerConnectionException('Bad server {0}; failed on reconnect'.format(config))

        db.echo = True

        logger.debug('Returning database instance: {0}'.format(db))

        return db

    def validate_connection(self, db):
        ''' Throws exception on invalid connection.'''

        logger.debug("Executing select 1")
        db.connection().execute("select 1")
        return True

    def set_db_config(self, db_string):
        ''' Set default database configuration so future calls to get_connection will get what you want. '''

        if db_string not in self.get_connection_config_list():
            raise ManagerConnectionException('Unknown database configuration {0}.'.format(db_string))

        if db_string != self.database_configuration:
            self.unset_engine()
            self.database_configuration = db_string

    def unset_engine(self):
        '''Unset (disconnect) the SQLAlchemy engine.'''

        logger.info("unset_engine")
        self.db_engine = None