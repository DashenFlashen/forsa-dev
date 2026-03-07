import typer

app = typer.Typer(help="Manage FORSA development environments.")


@app.command()
def version():
    """Print version."""
    typer.echo("forsa-dev 0.1.0")
