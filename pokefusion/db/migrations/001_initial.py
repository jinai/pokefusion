"""Peewee migrations -- 001_initial.py.

Some examples (model - class or model name)::

    > Model = migrator.orm['table_name']            # Return model in current state by name
    > Model = migrator.ModelClass                   # Return model in current state by name

    > migrator.sql(sql)                             # Run custom SQL
    > migrator.run(func, *args, **kwargs)           # Run python function with the given args
    > migrator.create_model(Model)                  # Create a model (could be used as decorator)
    > migrator.remove_model(model, cascade=True)    # Remove a model
    > migrator.add_fields(model, **fields)          # Add fields to a model
    > migrator.change_fields(model, **fields)       # Change fields
    > migrator.remove_fields(model, *field_names, cascade=True)
    > migrator.rename_field(model, old_field_name, new_field_name)
    > migrator.rename_table(model, new_table_name)
    > migrator.add_index(model, *col_names, unique=False)
    > migrator.add_not_null(model, *field_names)
    > migrator.add_default(model, field_name, default)
    > migrator.add_constraint(model, name, sql)
    > migrator.drop_index(model, *col_names)
    > migrator.drop_not_null(model, *field_names)
    > migrator.drop_constraints(model, *constraints)

"""

from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""
    
    @migrator.create_model
    class Server(pw.Model):
        id = pw.AutoField()
        discord_id = pw.IntegerField(unique=True)
        name = pw.CharField(max_length=255)
        prefix = pw.CharField(max_length=2)
        lang = pw.CharField(default='fr', max_length=2)
        joined_at = pw.DateTimeField()
        updated_at = pw.DateTimeField()
        active = pw.BooleanField(default=True)

        class Meta:
            table_name = "server"

    @migrator.create_model
    class Settings(pw.Model):
        id = pw.AutoField()
        global_seed = pw.IntegerField(default=0)
        updated_at = pw.DateTimeField()
        maintenance_mode = pw.BooleanField(default=False)

        class Meta:
            table_name = "settings"

    @migrator.create_model
    class User(pw.Model):
        id = pw.AutoField()
        discord_id = pw.IntegerField(unique=True)
        name = pw.CharField(max_length=255)
        seed = pw.IntegerField(default=0)
        updated_at = pw.DateTimeField()
        xmas_prompt = pw.BooleanField(default=False)
        xmas_rerolls = pw.IntegerField(default=0)
        xmas_delta = pw.IntegerField(default=0)
        bday_prompt = pw.BooleanField(default=False)
        bday_rerolls = pw.IntegerField(default=0)
        bday_delta = pw.IntegerField(default=0)
        free_rerolls = pw.IntegerField(default=0)

        class Meta:
            table_name = "user"


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""
    
    migrator.remove_model('user')

    migrator.remove_model('settings')

    migrator.remove_model('server')
