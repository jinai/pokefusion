"""Peewee migrations -- 003_remove_seeds.py.

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
    
    migrator.remove_fields('settings', 'global_seed')

    migrator.remove_fields('user', 'seed', 'xmas_rerolls', 'xmas_delta', 'bday_rerolls', 'bday_delta')

    @migrator.create_model
    class Totem(pw.Model):
        id = pw.AutoField()
        discord_id = pw.IntegerField(unique=True)
        head = pw.IntegerField(default=0)
        body = pw.IntegerField(default=0)
        updated_at = pw.DateTimeField()

        class Meta:
            table_name = "totem"


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""
    
    migrator.add_fields(
        'user',

        seed=pw.IntegerField(default=0),
        xmas_rerolls=pw.IntegerField(default=0),
        xmas_delta=pw.IntegerField(default=0),
        bday_rerolls=pw.IntegerField(default=0),
        bday_delta=pw.IntegerField(default=0))

    migrator.add_fields(
        'settings',

        global_seed=pw.IntegerField(default=0))

    migrator.remove_model('totem')
