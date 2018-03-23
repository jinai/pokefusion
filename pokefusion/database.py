import os
from collections import defaultdict

import pymongo


class Database:
    def __init__(self):
        self.client = pymongo.MongoClient(os.environ['DB_URL'])
        self.db = self.client.get_database()
        self.cache = {
            "guilds": defaultdict(dict)
        }

    def update_guild(self, guild, **kwargs):
        self.cache['guilds'][guild.id].update(kwargs)
        self.db.guilds.update({"_id": guild.id}, kwargs, upsert=True)

    def find_guild(self, guild):
        if guild.id in self.cache['guilds']:
            return self.cache['guilds'][guild.id]
        return self.db.guilds.find_one({"_id": guild.id})

    def __del__(self):
        self.client.close()
