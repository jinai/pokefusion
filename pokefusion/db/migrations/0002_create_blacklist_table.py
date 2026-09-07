from peewee import CharField, IntegerField, Model


def up(migrator, db):
    class Blacklist(Model):
        discord_id = IntegerField(unique=True)
        reason = CharField(null=True)

        class Meta:
            database = db
            table_name = "blacklist"

    db.create_tables([Blacklist])


def down(migrator, db):
    migrator.migrate(migrator.drop_table("blacklist"))
