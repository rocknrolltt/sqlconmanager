from nose.tools import assert_raises
import pkg_resources

from sqlconmanager.connection_manager import ManagerConnectionException, Manager, ConnectionLevel


def get_config_stream(template=False):
        if template:
            return pkg_resources.resource_stream('sqlconmanager', 'resources/dbconfig.yaml')

        return pkg_resources.resource_stream('sqlconmanager', 'tests/testdbconfig.yaml')

def create_table_schema():
    return "CREATE TABLE test (id int PRIMARY KEY AUTO_INCREMENT, name varchar(45))"


class TestConnectionManager():
    '''Connection manager testing class.'''

    @classmethod
    def setup_class(cls):
        '''create a new test table in database, populate it with one entry'''
        cls.mgr = Manager()
        config_stream = get_config_stream()
        print 'Config: {0}'.format(config_stream)
        conn = cls.mgr.get_connection(config_stream, security_level=ConnectionLevel.UPDATE)
        conn.execute(create_table_schema())
        conn.execute("INSERT INTO test (name) VALUES ('testing')")

    @classmethod
    def teardown_class(cls):
        '''drop created table in database'''
        config_stream = get_config_stream()
        conn = cls.mgr.get_connection(config_stream, security_level=ConnectionLevel.UPDATE)
        print 'Dropping table {0}'.format(conn)
        conn.execute("DROP TABLE test")
        cls.mgr.set_db_config('dev_test')
        cls.mgr.unset_engine()

    def test_setDBConfig(self):
        ''' This tests the interception of a bad configuration at setting time rather than at first request. '''
        assert_raises(ManagerConnectionException, self.mgr.set_db_config, 'tequilla')
        config_stream = get_config_stream()
        conn_cfg = "dev_test"

        self.mgr.set_db_config(conn_cfg)
        try:
            production_connection = self.mgr.get_connection(config_stream, config=conn_cfg)
            self.mgr.validate_connection(production_connection)
        except Exception:
            raise AssertionError('Unable to retrieve valid production connection')

        try:
            production_connection2 = self.mgr.get_connection(config_stream)
            self.mgr.validate_connection(production_connection2)
        except Exception:
            raise AssertionError('Unable to retrieve valid production connection')

    def test_valid_connection(self):
        config_stream = get_config_stream()
        conn = self.mgr.get_connection(config_stream, security_level=ConnectionLevel.UPDATE)
        entries = conn.test.all()
        print entries
        assert entries[0].name == 'testing'

        conn = self.mgr.get_connection(config_stream, security_level=ConnectionLevel.UPDATE)
        entries = conn.test.all()
        assert entries[0].name == 'testing'

    def test_no_new_connection(self):
        """
            since engine has already been created,even though we try to get an invalid connection, script will revert
            to already created engine, and return a valid connection
        """
        conn = self.mgr.get_connection("notstream")
        entries = conn.test.all()
        assert entries[0].name == 'testing'