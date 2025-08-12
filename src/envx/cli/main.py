import typer

from .service import app as service_app
from .worker import app as worker_app

app = typer.Typer()

app.add_typer(service_app, name="service")
app.add_typer(worker_app, name="worker")


if __name__ == "__main__":
    app()
