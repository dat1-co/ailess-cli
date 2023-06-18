from typing import Optional

import typer

from ailess import __app_name__, __version__
from ailess.modules.aws_utils import push_docker_image, print_endpoint_info
from ailess.modules.cli_utils import config_prompt
from ailess.modules.config_utils import save_config, load_config
from ailess.modules.docker_utils import generate_or_update_docker_ignore, generate_dockerfile, build_docker_image
from ailess.modules.env_utils import get_environment_config
from ailess.modules.python_utils import ensure_requirements_exists
from ailess.modules.terraform_utils import generate_terraform_file, generate_tfvars_file, ensure_tf_state_bucket_exists, \
    update_infrastructure, destroy_infrastructure

app = typer.Typer()

@app.command()
def init() -> None:
    """Initialize the project"""
    config = config_prompt()
    config = config | get_environment_config()
    save_config(config)
    print("✔    Config saved to .ailess/config.json")
    ensure_requirements_exists()
    print("✔    requirements.txt")
    generate_or_update_docker_ignore()
    print("✔    .dockerignore")
    generate_dockerfile(config)
    print("✔    Dockerfile")
    generate_tfvars_file(config)
    generate_terraform_file(config)
    print("✔    Terraform Cluster Config")
    print("🚀    done")

@app.command()
def deploy() -> None:
    """Deploy the project"""
    config = load_config()

    build_docker_image(config)
    push_docker_image(config)

    ensure_tf_state_bucket_exists()
    # todo:
    # check if the infrastructure is already deployed and update it if so or deploy the code
    update_infrastructure()
    print_endpoint_info(config)

    print("🚀    done")

@app.command()
def destroy() -> None:
    destroy_infrastructure()
    print("🚀    Done!")
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
