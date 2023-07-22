import os
import subprocess
import sys

import inquirer


def config_prompt():
    from .aws_utils import get_regions, get_predefined_instances
    from ailess.modules.aws_utils import get_instance_type_info

    print("Welcome to the Ailess CLI!")
    current_folder = os.path.basename(os.getcwd())
    questions = [
        inquirer.Text("project_name", message="What is your project name?", default=current_folder),
        inquirer.List(
            "aws_region",
            message="Choose an AWS region to deploy to",
            choices=get_regions(),
        ),
        inquirer.Text("host_port", message="What port is your app running on?", default=5000),
        inquirer.Text(
            "instances_count", message="How many servers in the cluster do you want to run?", default=2
        ),
        inquirer.List(
            "ec2_instance_type",
            message="Choose an EC2 instance (server) type",
            choices=get_predefined_instances(),
        ),
    ]
    answers = inquirer.prompt(questions)

    if answers["ec2_instance_type"] == "other (custom input)":
        custom_instance_answers = inquirer.prompt(
            [inquirer.Text("ec2_instance_type", message="Input EC2 instance type (e.g. t2.micro)")]
        )
        answers["ec2_instance_type"] = custom_instance_answers["ec2_instance_type"]
    else:
        answers["ec2_instance_type"] = answers["ec2_instance_type"].split(" ")[0]

    entrypoint_answers = inquirer.prompt(
        [
            inquirer.Path(
                "entrypoint_path",
                message="Where is your entrypoint file located? (e.g. app.py)",
                path_type=inquirer.Path.FILE,
            ),
        ]
    )

    answers["entrypoint_path"] = entrypoint_answers["entrypoint_path"]

    instance_data = get_instance_type_info(answers["ec2_instance_type"], answers["aws_region"])
    answers["cpu_architecture"] = instance_data["cpu_architecture"]
    answers["has_gpu"] = instance_data["num_gpus"] > 0

    return answers


def cuda_version_prompt():
    questions = [
        inquirer.Text(
            "cuda_version",
            message="You selected a GPU instance. Please enter an NVIDIA CUDA version to use",
            default="12.1",
        ),
    ]
    answers = inquirer.prompt(questions)
    return answers["cuda_version"]


def define_cuda_version():
    from ailess.modules.env_utils import get_cuda_version

    cuda_version = get_cuda_version()
    if cuda_version is None:
        cuda_version = cuda_version_prompt()

    return cuda_version


def run_command_in_working_directory(command, spinner, cwd=os.getcwd(), join_stdout_stderr=False):
    try:
        if join_stdout_stderr:
            completed_process = subprocess.run(
                command, shell=True, stdout=sys.stdout, stderr=subprocess.STDOUT, cwd=cwd
            )
        else:
            completed_process = subprocess.run(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd
            )

        # Check if the command was successful
        if completed_process.returncode == 0:
            return completed_process.stdout  # Command executed successfully, no need to display output

        if spinner is not None:
            spinner.fail("❌")
        # Command failed, print stdout and stderr
        sys.stdout.buffer.write(completed_process.stdout)  # Print stdout
        sys.stdout.buffer.write(completed_process.stderr)  # Print stderr
        exit(1)

    except Exception as e:
        if spinner is not None:
            spinner.fail("❌")
        print(f"Error executing command: {str(e)}")
        exit(1)
