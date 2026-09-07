from datetime import datetime

from peewee import DateTimeField, IntegerField, Model


def up(migrator, db):
    class Totem(Model):
        discord_id = IntegerField(unique=True)
        head = IntegerField(default=0)
        body = IntegerField(default=0)
        updated_at = DateTimeField(default=datetime.now)

        class Meta:
            database = db
            table_name = "totem"

    db.create_tables([Totem])
    migrator.migrate(migrator.drop_column("settings", "global_seed"))
    migrator.migrate(migrator.drop_column("user", "bday_delta"))
    migrator.migrate(migrator.drop_column("user", "bday_rerolls"))
    migrator.migrate(migrator.drop_column("user", "seed"))
    migrator.migrate(migrator.drop_column("user", "xmas_delta"))
    migrator.migrate(migrator.drop_column("user", "xmas_rerolls"))


def down(migrator, db):
    migrator.migrate(migrator.add_column("user", "xmas_rerolls", IntegerField(default=0)))
    migrator.migrate(migrator.add_column("user", "xmas_delta", IntegerField(default=0)))
    migrator.migrate(migrator.add_column("user", "seed", IntegerField(default=0)))
    migrator.migrate(migrator.add_column("user", "bday_rerolls", IntegerField(default=0)))
    migrator.migrate(migrator.add_column("user", "bday_delta", IntegerField(default=0)))
    migrator.migrate(migrator.add_column("settings", "global_seed", IntegerField(default=0)))
    migrator.migrate(migrator.drop_table("totem"))
