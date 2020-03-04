import pymongo
from bson import ObjectId
from abc import ABC, abstractmethod
from pbu.logger import Logger


class AbstractMongoStore(ABC):
    """
    Abstract base class for MongoDB stores. A store is represented by a collection in MongoDB and contains one type of
    documents, which can be represented by a MongoDocument sub-class.
    """

    def __init__(self, mongo_url, db_name, collection_name, deserialised_class, data_model_version):
        """
        Creates a new instance of this store providing credentials and behaviour parameters.
        :param mongo_url: the url to the mongo database (including credentials)
        :param db_name: the database name on the mongo database server
        :param collection_name: the collection name within the database selected
        :param deserialised_class: a sub-class of MongoDocument, which can be used to de-serialise documents in MongoDB
        into objects that can be handled easier.
        :param data_model_version: the data model version of this store.
        """
        # e.g. mongodb://localhost:27017
        self.mongo_url = mongo_url

        # connect
        client = pymongo.MongoClient(self.mongo_url)
        self.db = client[db_name]
        self.collection = self.db[collection_name]

        self.logger = Logger(self.__class__.__name__)
        self.object_class = deserialised_class
        self.data_model_version = data_model_version

    def create(self, document):
        """
        Creates a new document in the current store/collection.
        :param document: the document to provide either as dictionary or MongoDocument sub-class instance.
        :return: the id of the newly created document
        """
        if getattr(document, "to_json", None) is not None:
            document = document.to_json()

        if isinstance(document, dict):
            if "version" in document:
                document["version"] = self.data_model_version
            return str(self.collection.insert_one(document).inserted_id)
        raise ValueError("Provided document needs to be a dict or provide a to_json() method")

    def query(self, query):
        """
        Runs a query against the collection, expecting a list of matching documents to be returned. Documents will be
        parsed into MongoDocuments, if a object class is provided to the store on initialisation.
        :param query: the query to run provided as a dictionary
        :return: a list of parsed documents matching the query
        """
        if self.object_class is not None:
            return list(map(lambda doc: self.object_class.from_json(doc), self.collection.find(query)))

        # don't use serialisation
        return self.collection.find(query)

    def query_one(self, query):
        """
        Runs a query against the collection, expecting a single document to be returned. The result will be parsed into
        a MongoDocument, if the object class is provided on store initialisation.
        :param query: the query to run
        :return: the document that was returned by the database
        """
        result = self.collection.find_one(query)
        if result is None:
            return None

        if self.object_class is None:
            return result
        # parse the result into an object
        return self.object_class.from_json(result)

    def update_one(self, query, update):
        """
        Updates a single document, providing a query and an update set for the one document matching the query.
        :param query: the query to find which document to update
        :param update: the update of the document (provided as $set and $unset)
        :return: the result of the update operation
        """
        if "_id" in query and isinstance(query["_id"], str):
            query["_id"] = AbstractMongoStore.object_id(query["_id"])
        if "$set" in update and "_id" in update["$set"]:
            del update["$set"]["_id"]
        return self.collection.update_one(query, update)

    def update(self, query, update):
        """
        Updates a set of documents matching the provided query, applying the provided update to each matching document.
        :param query: the query expressed as dictionary to select the documents to update
        :param update: the update expressed as dictionary containing $set and/or $unset.
        :return: the result of the update operation
        """
        if "$set" in update and "_id" in update["$set"]:
            del update["$set"]["_id"]
        return self.collection.update(query, update)

    def update_full(self, document):
        if not isinstance(document, dict):
            if getattr(document, "to_json", None) is None:
                raise ValueError("Provided document needs to be a dict or have a to_json method.")
            document = document.to_json()
        return self.update_one(AbstractMongoStore.id_query(document["_id"]),
                               AbstractMongoStore.set_update_full(document))

    def get(self, doc_id):
        """
        Retrieves the document with the provided document ID
        :param doc_id: the document id to get
        :return:
        """
        return self.query_one(AbstractMongoStore.id_query(doc_id))

    def get_all(self):
        """
        Returns a list of all items in the current collection.
        :return: a list of documents, if an object class is provided the documents in that list are already parsed into
        the object class.
        """
        return self.query({})

    def delete(self, doc_id):
        """
        Deletes a specific document identified by its ID.
        :param doc_id: the id of the document to delete
        :return: the result of the remove operation
        """
        return self.collection.delete_one(AbstractMongoStore.id_query(str(doc_id)))

    def delete_many(self, query):
        return self.collection.delete_many(query)

    @staticmethod
    def list_to_json(item_list):
        """
        Helper class serialising a list of MongoDocuments into a list of dictionaries that can easily be serialised.
        :param item_list: a list of MongoDocument instances
        :return: a list of dictionaries.
        """
        return list(map(lambda item: item.to_json(), item_list))

    @staticmethod
    def object_id(string_id):
        """
        Creates a MongoDB ObjectId instance from a given string ID
        :param string_id: the id represented as string
        :return: the same id represented as ObjectId
        """
        return ObjectId(string_id)

    @staticmethod
    def id_query(string_id):
        """
        Returns a simple dictionary containing a query for the given id of a document
        :param string_id: the id of a document expressed as string
        :return: a dictionary containing a valid/proper id query for MongoDB.
        """
        return {"_id": AbstractMongoStore.object_id(string_id)}

    @staticmethod
    def set_update_full(set_update):
        """
        Creates an update statement that can be evaluated by MongoDB, including all keys of a dictionary passed in.
        :param set_update: a dictionary of all attributes/keys to be updated.
        :return: a dictionary containing a proper/valid update statement for MongoDB.
        """
        if "_id" in set_update:
            del set_update["_id"]
        return {
            "$set": set_update
        }

    @staticmethod
    def unset_update(keys):
        """
        Creates a delete query to remove certain keys from a document or list of documents.
        :param keys: a list of keys to delete (or a single key)
        :return: a dictionary containing a proper/valid update statement for MongoDB.
        """
        unset_update = {
            "$unset": {}
        }
        if isinstance(keys, str):
            unset_update[keys] = 1
        elif isinstance(keys, list):
            for key in keys:
                unset_update[key] = 1
        return unset_update

    @staticmethod
    def set_update(keys, values):
        """
        Creates an update query to update a list of keys with a set of values.
        :param keys: a list of string keys or a single string key to update.
        :param values: a list of values or a single value to update. The values will be matched to keys by index.
        :return: a dictionary containing proper/valid update statement for MongoDB.
        """
        set_update = {
            "$set": {}
        }

        if isinstance(keys, str):
            set_update["$set"][keys] = values
        elif isinstance(keys, list):
            for index, key in enumerate(keys):
                set_update["$set"][key] = values[index]

        return set_update


class AbstractMongoDocument(ABC):
    """
    Abstract parent class for classes representing the objects in a specific MongoDB collection.
    """
    def __init__(self, doc_id=None, data_model_version=None):
        """
        Parent constructor initialising the id and version attributes of this instance.
        :param doc_id: the id under which the object is stored in the database
        :param data_model_version: the current data model version in the system
        """
        self.id = doc_id
        if self.id is not None and not isinstance(self.id, str):
            # convert ObjectId to str
            self.id = str(self.id)
        self.version = data_model_version

    def extract_system_fields(self, json):
        """
        Extracts the id and version from a JSON object or dictionary and maps them to the current instances attributes.
        :param json: the json object or dictionary from which to extract information.
        """
        if "_id" in json:
            self.id = str(json["_id"])
        if "version" in json:
            self.version = json["version"]

    @abstractmethod
    def to_json(self):
        """
        Returns a serializable representation of this document as dictionary or JSON object.
        :return: a dictionary or JSON object providing the data contained within this document
        """
        result = {}
        if self.id is not None:
            result["_id"] = str(self.id)
        if getattr(self, "version", None) is not None:
            result["version"] = self.version
        return result

    @staticmethod
    @abstractmethod
    def from_json(json):
        """
        Receives a dictionary or JSON object and returns an instance of this MongoDocument sub-class.
        :param json: a dictionary or JSON object instance
        :return: an instance of a sub-class of MongoDocument
        """
        pass
