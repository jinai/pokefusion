def up(migrator, db):
    migrator.migrate(migrator.rename_column("settings", "maintenance_mode", "maintenance"))


def down(migrator, db):
    migrator.migrate(migrator.rename_column("settings", "maintenance", "maintenance_mode"))
