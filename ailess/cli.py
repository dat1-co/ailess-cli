from typing import Optional

import typer
import inquirer

from ailess import __app_name__, __version__
from .aws_utils import get_regions

app = typer.Typer()

@app.command()
def init() -> None:
    """Initialize the project"""
    questions = [
        inquirer.List('aws_region',
                      message="Choose an AWS region to deploy to",
                      choices=get_regions(),
                      ),
    ]
    answers = inquirer.prompt(questions)
    print(answers)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"{__app_name__} v{__version__}")
        raise typer.Exit()

@app.callback()
def main(
        version: Optional[bool] = typer.Option(
            None,
            "--version",
            "-v",
            help="Show ailess CLI version and exit.",
            callback=_version_callback,
            is_eager=True,
        )
) -> None:
    return
