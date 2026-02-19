import typer

from pokefusion.cli.db import db_app
from pokefusion.cli.migrations import migrations_app
from pokefusion.cli.run import run_bot
from pokefusion.cli.tools import tools_app

app = typer.Typer(no_args_is_help=True)

app.command("run")(run_bot)
app.add_typer(migrations_app, name="migrations")
app.add_typer(db_app, name="db")
app.add_typer(tools_app, name="tools")

if __name__ == "__main__":
    app()
