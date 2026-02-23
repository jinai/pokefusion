"""Peewee migrations -- 004_pluralize_table_names.py.

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

    migrator.rename_table('server', 'servers')

    migrator.sql('DROP INDEX server_discord_id')

    migrator.sql('CREATE UNIQUE INDEX "servers_discord_id" ON "servers" ("discord_id")')

    migrator.rename_table('totem', 'totems')

    migrator.sql('DROP INDEX totem_discord_id')

    migrator.sql('CREATE UNIQUE INDEX "totems_discord_id" ON "totems" ("discord_id")')

    migrator.rename_table('user', 'users')

    migrator.sql('DROP INDEX user_discord_id')

    migrator.sql('CREATE UNIQUE INDEX "users_discord_id" ON "users" ("discord_id")')


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    migrator.rename_table('users', 'user')

    migrator.sql('DROP INDEX users_discord_id')

    migrator.sql('CREATE UNIQUE INDEX "user_discord_id" ON "user" ("discord_id")')

    migrator.rename_table('totems', 'totem')

    migrator.sql('DROP INDEX totems_discord_id')

    migrator.sql('CREATE UNIQUE INDEX "totem_discord_id" ON "totem" ("discord_id")')

    migrator.rename_table('servers', 'server')

    migrator.sql('DROP INDEX servers_discord_id')

    migrator.sql('CREATE UNIQUE INDEX "server_discord_id" ON "server" ("discord_id")')
