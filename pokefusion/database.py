import os
from collections import defaultdict

import pymongo


class Database:
    def __init__(self):
        self.client = pymongo.MongoClient(os.environ['DB_URL'])
        self.db = self.client.get_database()
        self.cache = {
            "settings": defaultdict(dict),
            "guilds": defaultdict(dict),
            "users": defaultdict(dict)
        }

    def update_settings(self, **kwargs):
        self._update_document(collection="settings", doc_id=1, **kwargs)

    def get_settings(self):
        return self._find_document(collection="settings", doc_id=1)

    def update_guild(self, guild, **kwargs):
        self._update_document(collection="guilds", doc_id=guild.id, **kwargs)

    def find_guild(self, guild):
        return self._find_document(collection="guilds", doc_id=guild.id)

    def update_user(self, user, **kwargs):
        self._update_document(collection="users", doc_id=user.id, **kwargs)

    def find_user(self, user):
        return self._find_document(collection="users", doc_id=user.id)

    def _update_document(self, *, collection, doc_id, **kwargs):
        self.cache[collection][doc_id].update(kwargs)
        self.db.get_collection(collection).update({"_id": doc_id}, {"$set": kwargs}, upsert=True)

    def _find_document(self, *, collection, doc_id):
        if doc_id in self.cache[collection]:
            return self.cache[collection][doc_id]

        doc = self.db.get_collection(collection).find_one({"_id": doc_id})
        doc = doc if doc is not None else {}
        self.cache[collection][doc_id].update(doc)
        return doc

    def __del__(self):
        self.client.close()
