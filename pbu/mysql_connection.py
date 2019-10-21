from mysql.connector.pooling import MySQLConnectionPool, PooledMySQLConnection
from mysql.connector import connect
from mysql.connector.errors import OperationalError, PoolError
from pbu.logger import Logger


class MysqlConnection:
    """
    Wrapper object for the MySQL connection.
    """

    def __init__(self, host, database, user, password):
        """
        Creates a new instance of a MySQL connection with its own connection pool.
        :param host: the mysql server
        :param database: the database on the mysql server
        :param user: the username for the mysql server
        :param password: the password for the mysql server
        """
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.logger = Logger(self.__class__.__name__)
        self.connection_pool = MySQLConnectionPool(pool_name="pynative_pool", pool_size=20, pool_reset_session=True,
                                                   host=host, database=database, user=user, password=password)

    def create_connection(self):
        """
        Opens a new connection to MySQL
        :return: the established connection
        """
        connection = connect(
            host=self.host,
            database=self.database,
            user=self.user,
            passwd=self.password,
            auth_plugin="mysql_native_password"
        )
        return connection

    def get_connection(self):
        """
        Retrieves a connection from the connection pool or forces to create a new connection. These connections will be
        returned to the connection pool, if you close them.
        :return: a pooled mysql connection
        """
        try:
            con = self.connection_pool.get_connection()
            if not con.is_connected():
                # attempt to fetch a different connection
                return self.get_connection()
            return con
        except PoolError as pe:
            # no connection available
            self.logger.exception("No connection available: {}".format(pe))
            return self._get_new_connection(con)

    def _get_new_connection(self):
        """
        Creates a new pooled mysql connection and adds it to the existing connection pool.
        :return: a pooled mysql connection
        """
        connection = self.create_connection()
        pooled_connection = PooledMySQLConnection(self.connection_pool, connection)
        return pooled_connection

    def cursor(self, prepared=False):
        """
        Proxy to create a new cursor.
        :param prepared: boolean flag whether this cursor is a prepared statement cursor
        :return: a tuple containing a cursor allowing for DB access and the connection
        """
        try:
            connection = self.connection_pool.get_connection()
            cursor = connection.cursor(prepared)
            return cursor, connection
        except PoolError as pe:
            # no connection in pool or pool full
            self.logger.exception("No connection in pool or pool full: {}".format(pe))
        except OperationalError as oe:
            # reconnect in case of disconnect after a while
            self.logger.exception("Operational error: {}".format(oe))
