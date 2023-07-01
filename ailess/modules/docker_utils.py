import os
import subprocess
import sys
import threading

import docker
import signal

from ailess.modules.cli_utils import run_command_in_working_directory
from yaspin import yaspin

DOCKER_ARCHITECTURE_AMD64 = "linux/amd64"
DOCKER_ARCHITECTURE_ARM64 = "linux/arm64"

def generate_dockerfile(config):
    # TODO: generate dockerfile based on config and cuda version
    dockerfile_content = []
    dockerfile_content.append("FROM python:3.9.16")
    dockerfile_content.append("ADD requirements.txt /app/requirements.txt")
    dockerfile_content.append("WORKDIR /app")
    dockerfile_content.append("RUN pip install -r requirements.txt")
    dockerfile_content.append("ADD . /app")
    dockerfile_content.append("CMD [\"python3\", \"-u\", \"{}\"]".format(config["entrypoint_path"]))
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



def start_docker_container(config):
    from ailess.modules.terraform_utils import convert_to_alphanumeric
    client = docker.from_env()
    try:
        stop_container(config)
    except docker.errors.NotFound:
        pass
    environment = {'NVIDIA_VISIBLE_DEVICES': 'all'} if config['has_gpu'] else None
    container = client.containers.run(
        convert_to_alphanumeric(config["project_name"]),  # Replace with the name or ID of your Docker image
        name=convert_to_alphanumeric(config["project_name"]),
        ports={'{}/tcp'.format(config["host_port"]): config["host_port"]},
        environment=environment,
        detach=True,
    )

    print("✔     container started at http://localhost:{}".format(config["host_port"]))
    def print_logs():
        for log in container.logs(stream=True):
            print(log.decode().strip())

    log_thread = threading.Thread(target=print_logs)
    log_thread.start()

    container.wait()
    container.stop()
    log_thread.join()
    container.remove()


def stop_container(config):
    from ailess.modules.terraform_utils import convert_to_alphanumeric
    client = docker.from_env()
    container = client.containers.get(convert_to_alphanumeric(config["project_name"]))
    container.stop()
    container.remove()

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
