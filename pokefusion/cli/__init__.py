import typer

env_option = typer.Option(
    ...,
    "--env",
    help="Target environment",
    case_sensitive=False
)
