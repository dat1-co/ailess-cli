import os
import subprocess
import sys
import urllib.request, json
import re

from ailess.modules.cli_utils import run_command_in_working_directory
from yaspin import yaspin

DOCKER_ARCHITECTURE_AMD64 = "linux/amd64"
DOCKER_ARCHITECTURE_ARM64 = "linux/arm64"

def get_image_name_from_config(config):
    cuda_version = config["cuda_version"]
    if cuda_version is None:
        return "python:3.9"
    else:
        response = urllib.request.urlopen(f"https://hub.docker.com/v2/repositories/nvidia/cuda/tags/?name={cuda_version}&page_size=100")
        image_names = list(map(lambda result: result["name"], json.load(response)["results"]))
        pattern = r'^(\d+\.\d+)(\.\d+)?-devel-ubuntu(\d+\.\d+)$'
        filtered_images = [image for image in image_names if re.match(pattern, image)]
        sorted_images = sorted(filtered_images, key=lambda x: x.split('-')[0] + x.split('-')[-1], reverse=True)
        if len(sorted_images) == 0:
            print(f"Could not find a suitable docker image for cuda version {cuda_version}")
            exit(1)
        latest_image = sorted_images[0]
        return f"nvidia/cuda:{latest_image}"

def generate_dockerfile(config):
    # TODO: generate dockerfile based on config and cuda version
    dockerfile_content = []
    dockerfile_content.append("FROM {}".format(get_image_name_from_config(config)))
    if config["cuda_version"] is not None:
        dockerfile_content.append("""
ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && \
    apt install -y bash \
                   build-essential \
                   curl \
                   ca-certificates \
                   python3 \
                   python3-pip \
""")

    dockerfile_content.append("ADD requirements.txt /app/requirements.txt")
    dockerfile_content.append("WORKDIR /app")
    dockerfile_content.append("RUN pip3 install -r requirements.txt")
    dockerfile_content.append("ADD . /app")
    dockerfile_content.append("CMD [\"python3\", \"{}\"]".format(config["entrypoint_path"]))
    with open(".ailess/Dockerfile", "w") as dockerfile:
        dockerfile.write("\n".join(dockerfile_content))


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
    with yaspin(text="    building docker image") as spinner:
        run_command_in_working_directory(
            "docker buildx build \
            --platform {} \
            -t {}:latest \
            -f {} . --load"
            .format(
                config["cpu_architecture"],
                convert_to_alphanumeric(config["project_name"]),
                os.path.join(".ailess", "Dockerfile")
            ), spinner)
        spinner.ok("✔")


def login_to_docker_registry(username, password, registry_url, spinner):
    login_cmd = f"docker login --username {username} --password-stdin {registry_url}"

    # Create a subprocess and execute the login command
    proc = subprocess.Popen(login_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            shell=True)

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
