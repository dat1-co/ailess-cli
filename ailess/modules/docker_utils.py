import json
import os
import re
import subprocess
import sys
import urllib.request

from yaspin import yaspin

from ailess.modules.cli_utils import run_command_in_working_directory
from ailess.modules.python_utils import RequirementsParser
from ailess.modules.docker_searchers import get_sercher_from_config

DOCKER_ARCHITECTURE_AMD64 = "linux/amd64"
DOCKER_ARCHITECTURE_ARM64 = "linux/arm64"


def generate_dockerfile(config):
    if os.path.exists(os.path.join(os.getcwd(), "Dockerfile")):
        return

    # Get image name from config
    requirements = RequirementsParser("requirements.txt")
    searcher = get_sercher_from_config(config, requirements)
    image_name = searcher.get_image_name(config, requirements)
    image_extras = searcher.get_image_extras()
    
    dockerfile_content = []
    dockerfile_content.append("FROM {}".format(image_name))
    if config["has_gpu"]:
        dockerfile_content.append(
"""
ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && \
    apt install -y bash \
                   build-essential \
                   curl \
                   ca-certificates \
                   python3 \
                   python3-pip \
"""
        )

    dockerfile_content.append(image_extras)
    dockerfile_content.append("RUN apt-get update && apt-get install libgl1 -y")
    dockerfile_content.append("ADD requirements.txt /app/requirements.txt")
    dockerfile_content.append("WORKDIR /app")
    dockerfile_content.append("RUN pip3 install -r requirements.txt")
    dockerfile_content.append("ADD . /app")
    dockerfile_content.append('CMD ["python3", "-u", "{}"]'.format(config["entrypoint_path"]))
    with open("Dockerfile", "w") as dockerfile:
        dockerfile.write("\n".join(dockerfile_content))


def generate_docker_compose_file(config):
    if os.path.exists(os.path.join(os.getcwd(), "docker-compose.yml")):
        return

    from ailess.modules.terraform_utils import convert_to_alphanumeric

    docker_compose_content = """services:
  {}:
    environment:
      - PYTHONUNBUFFERED=1
    image: {}:latest
    build: .
    platform: {}
    ports:
      - "{}:{}"
    """.format(
        convert_to_alphanumeric(config["project_name"]),
        convert_to_alphanumeric(config["project_name"]),
        config["cpu_architecture"],
        config["host_port"],
        config["host_port"],
    )

    if config["has_gpu"]:
        docker_compose_content += """
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
"""
    with open("docker-compose.yml", "w") as dockerfile:
        dockerfile.write(docker_compose_content)


def generate_or_update_docker_ignore():
    if os.path.exists(".dockerignore"):
        with open(".dockerignore", "r") as f:
            docker_ignore = f.read()
            if ".ailess/*" not in docker_ignore:
                with open(".dockerignore", "a") as docker_ignore_file:
                    docker_ignore_file.write(".ailess/*")
            if ".idea/*" not in docker_ignore:
                with open(".dockerignore", "a") as docker_ignore_file:
                    docker_ignore_file.write(".idea/*")
    else:
        with open(".dockerignore", "w") as docker_ignore_file:
            docker_ignore_file.write(".ailess/*\n.idea/*")


def build_docker_image(config):
    from ailess.modules.terraform_utils import convert_to_alphanumeric

    dockerfile_path = os.path.join(os.getcwd(), "Dockerfile")

    with yaspin(text="    building docker image") as spinner:
        run_command_in_working_directory(
            "docker buildx build \
            --platform {} \
            -t {}:latest \
            -f {} . --load".format(
                config["cpu_architecture"],
                convert_to_alphanumeric(config["project_name"]),
                dockerfile_path,
            ),
            spinner,
        )
        spinner.ok("✔")


def start_docker_container(config):
    stop_container()
    print("✔     starting container at http://localhost:{}".format(config["host_port"]))
    run_command_in_working_directory("docker compose up", None, os.getcwd(), True)


def stop_container():
    run_command_in_working_directory("docker compose down", None)


def login_to_docker_registry(username, password, registry_url, spinner):
    login_cmd = f"docker login --username {username} --password-stdin {registry_url}"

    # Create a subprocess and execute the login command
    proc = subprocess.Popen(
        login_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )

    # Pass the password to the subprocess via stdin
    stdout, stderr = proc.communicate(input=password.encode())

    # Check the output to determine if the login was successful
    if proc.returncode == 0:
        return
    else:
        spinner.fail("❌")
        # Command failed, print stdout and stderr
        sys.stdout.buffer.write(stdout)  # Print stdout
        sys.stderr.buffer.write(stderr)  # Print stderr
        exit(1)
