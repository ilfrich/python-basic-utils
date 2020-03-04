from datetime import datetime
from mysql.connector.errors import OperationalError, PoolError
from pbu.logger import Logger
from pbu.mongo_store import AbstractMongoDocument
from abc import ABC, abstractmethod
from tzlocal import get_localzone

_DELETE_STATEMENT = "delete from {} where {}=%s"
_SELECT_STATEMENT = "select {} from {}"
_WHERE_STATEMENT = "{} where {}".format(_SELECT_STATEMENT, "{}")
_UPDATE_STATEMENT = "update {} set {} where {}"


class AbstractMysqlStore(ABC):
    """
    Parent class for all MySQL stores. Each store represents a single database table containing a specific business
    object
    """

    DATE_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, connection, table_name, object_class, log_folder=None):
        """
        Parent constructor to store the connection and table name for this store.
        :param connection: an active MySQL connection
        :param table_name: the name of the table to use for this store
        :param object_class: the class name that represents the objects stored in this database
        :param log_folder: an optional log folder, where the mysql store should log its messages to using the python
        logging framework
        """
        self.connection = connection
        self.table_name = table_name
        self.object_class = object_class
        if log_folder is None:
            self.logger = Logger(name=self.__class__.__name__)
        else:
            self.logger = Logger(name=self.__class__.__name__, log_folder=log_folder)

    def check_exists(self, definition):
        """
        Initialisation method to check whether the specified table exists. If not the definition passed is used to
        create the new table.
        :param definition: a create table statement with a placeholder for the table name
        """
        # create new cursor
        cursor, connection = self.connection.cursor()

        # execute show tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        # check if the table already exists
        contains = False
        for table_name in tables:
            # unpack table name from result
            t_name = table_name[0]
            if t_name == self.table_name:
                self.logger.info("[SQL] Table '{}' already exists.".format(self.table_name))
                contains = True

        if not contains:
            # table doesn't exist, load definition from resource file
            definition = definition.decode('utf-8').replace("\n", "").format(self.table_name)
            # create table
            self.logger.info("[SQL] Creating table '{}'.".format(self.table_name))
            self.logger.info("[SQL] {}".format(definition))
            cursor.execute(definition)
            self.close(cursor, connection, True)
            return

        self.close(cursor, connection)

    def run_invoke(self, update, params=None, debug=False):
        """
        Runs a statement with given parameters and commits the transaction. This is meant for insert, update and delete
        statements.
        :param update: the sql statement without replaced table name
        :param params: either a tuple of the params for the statement or a list of tuples for multiple executions of the
        statement
        :param debug: boolean flag indicating whether we log the full resolved statement during the execution
        :return the id of the last inserted row, if available, otherwise None.
        """
        cursor, connection = self.connection.cursor(prepared=True)
        statement = update.format(self.table_name)
        result = None
        try:
            if params is None:
                # insert/update without params
                cursor.execute(statement)
            elif isinstance(params, list):
                # insert/update multiple records
                cursor.executemany(statement, params)
            else:
                # insert/update single record
                cursor.execute(statement, params)
            if debug:
                self.logger.info(cursor.statement)

            result = cursor.lastrowid

            self.close(cursor, connection, True)
        except (PoolError, OperationalError, BaseException) as except1:
            # something went wrong, ensure connection is closed
            self.logger.exception("Error running invoke: {}".format(statement))
            self.handle_exception(except1, cursor, connection)

        return result

    def run_query(self, query, params=None, extract_function=None, debug=False):
        """
        Runs the given query and unpacks row data into objects as specified by the lambda passed as extract function.
        :param query: the select query statement with a placeholder for the table name (replacing {})
        :param params: any query params (will replace occurrences of %s)
        :param extract_function: a static function that converts a MySQL row returned by the given query into an object
        :param debug: boolean flag indicating whether we log the full resolved statement during the execution
        :return: a list of extracted objects matching the query and parameter statement
        """
        result = []

        cursor, connection = self.connection.cursor(prepared=True)
        statement = query.format(self.table_name)
        try:
            if params is None:
                cursor.execute(statement)
            else:
                cursor.execute(statement, params)
            if debug:
                self.logger.info(cursor.statement)
            res = cursor.fetchall()
            self.close(cursor, connection)
        except (PoolError, OperationalError, BaseException) as except1:
            self.logger.exception("Error running query: {}".format(query.format(self.table_name)))
            self.handle_exception(except1, cursor, connection)

        # process result
        if res is None:
            return []

        for row in res:
            if extract_function is not None:
                result.append(extract_function(row))
            else:
                result.append(row)
        return result

    def delete(self, row_id, id_field="id"):
        """
        Deletes a given record from this table
        :param row_id: the primary key of the row to delete
        :param id_field: the column name of the primary key
        """
        cursor, connection = self.connection.cursor(prepared=True)
        try:
            cursor.execute(_DELETE_STATEMENT.format(self.table_name, id_field), (row_id,))
            self.close(cursor, connection, True)
        except (PoolError, OperationalError, BaseException) as except1:
            self.logger.exception(
                "Error deleting item: {} / {}".format(_DELETE_STATEMENT.format(self.table_name, row_id)))
            self.handle_exception(except1, cursor, connection)

    def get(self, row_id, id_field="id"):
        """
        Retrieves a single row from the database.
        :param row_id: the primary key of the row to extract
        :param id_field: the column name of the primary key
        :return the parsed row object or None, if the row doesn't exist
        """
        result = self.run_query(self.create_select_query(where_clause="{} = %s".format(id_field)), (row_id,),
                                extract_function=self.object_class.from_row)
        if len(result) == 0:
            return None
        return result[0]

    def get_all(self):
        """
        Retrieves all records from a table.
        :return: a list of parsed row objects from this store's table.
        """
        return self.run_query(self.create_select_query(), extract_function=self.object_class.from_row)

    def handle_exception(self, except1, cursor, connection):
        """
        Handler function for database errors during execution of statements.
        :param except1: the original exception during SQL execution
        :param cursor: the current cursor
        :param connection: the current connection
        :raise Exception: the original exception that triggered the execution of this handler or a new exception caused
        by the handler function's attempt to close connections.
        """
        if cursor is None and connection is None:
            return
        try:
            # close connection and re-raise original exception
            self.close(cursor, connection)
            raise except1
        except (PoolError, OperationalError, BaseException) as except2:
            # couldn't close connection, raise new exception on top of the other
            self.logger.exception("Failed to close connection during exception handler")
            raise except2

    def get_field_list(self):
        """
        Retrieves the list of fields from the object class provided to the store. If the object class is not set or
        doesn't return a list of fields, an error is raised.
        :raise AttributeError or ValueError if the object class is not properly configured.
        :return: a list of strings
        """
        if self.object_class is None:
            raise AttributeError("No object class provided for this store.")
        fields = self.object_class.get_fields()
        if not isinstance(fields, list):
            raise ValueError("Object class doesn't provide a list of fields.")

        return fields

    def create_select_query(self, where_clause: str = None):
        """
        Returns a full query for selects adding in the fields and potential where-clause (optional)
        :param where_clause: an optional where clause (everything after the WHERE in an SQL statement)
        :return: a string representing the full query with all variables resolved.
        """
        if where_clause is None:
            return _SELECT_STATEMENT.format(", ".join(self.get_field_list()), self.table_name)

        return _WHERE_STATEMENT.format(", ".join(self.get_field_list()), self.table_name, where_clause)

    @classmethod
    def close(cls, cursor, connection, commit=False):
        """
        Closes the cursor and the connection. If the commit flag is set, before closing the cursor, the current
        transaction will be committed. When a pooled connection is closed, the connection will just be returned to the
        pool.
        :param cursor: a currently active cursor
        :param connection: a currently active connection
        :param commit: an optional boolean flag to show whether to commit or not before closing the connection/cursor
        """
        if connection is None or cursor is None:
            return
        if commit:
            connection.commit()
        cursor.close()
        connection.close()

    @staticmethod
    def parse_to_date(date_string):
        """
        Parses a mysql date or datetime string to a datetime object. The function detects automatically, which format is
        used and parse it accordingly.
        :param date_string: the date or datetime string
        :return: a datetime object of the parsed date
        """
        # short string, only date
        if len(date_string) == 10:
            dt = datetime.strptime(date_string, AbstractMysqlStore.DATE_FORMAT)

        # longer string, date + time
        elif len(date_string) == 19:
            dt = datetime.strptime(date_string, AbstractMysqlStore.DATETIME_FORMAT)

        # localise and return
        local_datetime = get_localzone().localize(dt)
        return local_datetime

    @staticmethod
    def parse_to_timestamp(date_string):
        """
        Parse a date or datetime string into a unix timestamp, respecting the timezone of the current server.
        :param date_string: the date or date time string
        :return: an integer representing the date or datetime string.
        """
        if isinstance(date_string, datetime):
            # already a datetime object
            return date_string.timestamp()
        # parse to datetime and then return timestamp
        local_datetime = AbstractMysqlStore.parse_to_date(date_string)
        return round(local_datetime.timestamp())

    @staticmethod
    def format_to_datetime(timestamp):
        """
        Formats a timestamp or datetime object into a mysql datetime string
        :param timestamp: a unix timestamp or a datetime object
        :return: the timestamp or datetime object represented as a string
        """
        # handle int/float timestamps
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
        # handle dates
        if isinstance(timestamp, datetime):
            dt = timestamp
        # localise and format
        localized = get_localzone().localize(dt)
        return datetime.strftime(localized, AbstractMysqlStore.DATETIME_FORMAT)

    @staticmethod
    def list_to_json(object_list):
        """
        Converts a list of model objects into a list of dictionaries representing the data contained in those model
        objects.
        :param object_list: a list of model objects
        :return: a list of dictionaries
        """
        result = []
        for item in object_list:
            result.append(item.to_json())
        return result


class AbstractMysqlDocument(AbstractMongoDocument):
    @staticmethod
    @abstractmethod
    def from_row(row):
        """
        Parses a MySQL result row into an AbstractMysqlDocument
        :param row: a mysql row (list of values)
        :return: an instance of a sub-class of AbstractMysqlDocument
        """
        pass

    @staticmethod
    @abstractmethod
    def get_fields():
        """
        Provides a list of MySQL column names used for the table storing this type of object.
        :return: a list of strings representing the column names
        """
        pass
