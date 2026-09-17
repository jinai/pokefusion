import typer

from pokefusion.cli.assets import assets_app
from pokefusion.cli.dex import dex_app
from pokefusion.cli.run import run_bot

app = typer.Typer(no_args_is_help=True)

app.command("run")(run_bot)
app.add_typer(dex_app, name="dex")
app.add_typer(assets_app, name="assets")
