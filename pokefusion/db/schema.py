from .database import database
from .models import Blacklist, Server, Settings, Totem, User

MODELS = [Settings, Server, User, Blacklist, Totem]


def create_schema(drop_tables: bool = False):
    with database:
        if drop_tables:
            database.drop_tables(MODELS)
        database.create_tables(MODELS)
