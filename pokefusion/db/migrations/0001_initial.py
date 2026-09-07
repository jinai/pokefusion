from datetime import datetime

from peewee import BooleanField, CharField, DateTimeField, IntegerField, Model


def up(migrator, db):
    class Settings(Model):
        global_seed = IntegerField(default=0)
        updated_at = DateTimeField(default=datetime.now)
        maintenance_mode = BooleanField(default=False)

        class Meta:
            database = db
            table_name = "settings"

    class Server(Model):
        discord_id = IntegerField(unique=True)
        name = CharField()
        prefix = CharField(max_length=2)
        lang = CharField(max_length=2, default="fr")
        joined_at = DateTimeField(default=datetime.now)
        updated_at = DateTimeField(default=datetime.now)
        active = BooleanField(default=True)

        class Meta:
            database = db
            table_name = "server"

    class User(Model):
        discord_id = IntegerField(unique=True)
        name = CharField()
        seed = IntegerField(default=0)
        updated_at = DateTimeField(default=datetime.now)
        xmas_prompt = BooleanField(default=False)
        xmas_rerolls = IntegerField(default=0)
        xmas_delta = IntegerField(default=0)
        bday_prompt = BooleanField(default=False)
        bday_rerolls = IntegerField(default=0)
        bday_delta = IntegerField(default=0)
        free_rerolls = IntegerField(default=3)

        class Meta:
            database = db
            table_name = "user"

    db.create_tables([Settings, Server, User])


def down(migrator, db):
    migrator.migrate(migrator.drop_table("user"))
    migrator.migrate(migrator.drop_table("server"))
    migrator.migrate(migrator.drop_table("settings"))
