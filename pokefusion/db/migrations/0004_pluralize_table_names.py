def up(migrator, db):
    migrator.migrate(migrator.rename_table("server", "servers"))
    migrator.migrate(migrator.drop_index("servers", "server_discord_id"))
    migrator.migrate(migrator.add_index("servers", ("discord_id",), unique=True, name="servers_discord_id"))

    migrator.migrate(migrator.rename_table("user", "users"))
    migrator.migrate(migrator.drop_index("users", "user_discord_id"))
    migrator.migrate(migrator.add_index("users", ("discord_id",), unique=True, name="users_discord_id"))

    migrator.migrate(migrator.rename_table("totem", "totems"))
    migrator.migrate(migrator.drop_index("totems", "totem_discord_id"))
    migrator.migrate(migrator.add_index("totems", ("discord_id",), unique=True, name="totems_discord_id"))


def down(migrator, db):
    migrator.migrate(migrator.drop_index("totems", "totems_discord_id"))
    migrator.migrate(migrator.add_index("totems", ("discord_id",), unique=True, name="totem_discord_id"))
    migrator.migrate(migrator.rename_table("totems", "totem"))

    migrator.migrate(migrator.drop_index("users", "users_discord_id"))
    migrator.migrate(migrator.add_index("users", ("discord_id",), unique=True, name="user_discord_id"))
    migrator.migrate(migrator.rename_table("users", "user"))

    migrator.migrate(migrator.drop_index("servers", "servers_discord_id"))
    migrator.migrate(migrator.add_index("servers", ("discord_id",), unique=True, name="server_discord_id"))
    migrator.migrate(migrator.rename_table("servers", "server"))
