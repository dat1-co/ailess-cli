import os


def generate_dockerfile(config):
    dockerfile_content = []
    dockerfile_content.append("FROM {}-devel-ubuntu22.04".format(config["cuda_version"]))
    dockerfile_content.append("ADD . /app")
    dockerfile_content.append("WORKDIR /app")
    dockerfile_content.append("RUN pip install -r requirements.txt")
    dockerfile_content.append("CMD python {}".format(config["entrypoint_path"]))
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
