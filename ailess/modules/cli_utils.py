import os
import subprocess
import sys

import inquirer

def config_prompt():
    from .aws_utils import get_regions, get_predefined_instances
    print("Welcome to the ailess.dev CLI configuration wizard!")
    current_folder = os.path.basename(os.getcwd())
    questions = [
        inquirer.Text('project_name', message="What is your project name?", default=current_folder),
        inquirer.List('aws_region',
                      message="Choose an AWS region to deploy to",
                      choices=get_regions(),
                      ),
        inquirer.Text('host_port', message="What port is your app running on?", default=5000),
        inquirer.Text('instances_count', message="How many servers in the cluster do you want to run?", default=2),
        inquirer.List('ec2_instance_type',
                      message="Choose an EC2 instance (server) type",
                      choices=get_predefined_instances(),
                      ),
    ]
    answers = inquirer.prompt(questions)

    if answers['ec2_instance_type'] == 'other (custom input)':
        custom_instance_answers = inquirer.prompt([inquirer.Text('ec2_instance_type', message="Input EC2 instance type (e.g. t2.micro)")])
        answers['ec2_instance_type'] = custom_instance_answers['ec2_instance_type']
    else:
        answers['ec2_instance_type'] = answers['ec2_instance_type'].split(' ')[0]

    entrypoint_answers = inquirer.prompt([
        inquirer.Path('entrypoint_path',
                      message="Where is your entrypoint file located? (e.g. app.py)",
                      path_type=inquirer.Path.FILE,
                      ),
    ])

    answers['entrypoint_path'] = entrypoint_answers['entrypoint_path']

    answers['cuda_version'] = '11.6.2'

    return answers


def run_command_in_working_directory(command, spinner):
    try:
        # Run the command silently, redirecting output
        completed_process = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.getcwd())

        # Check if the command was successful
        if completed_process.returncode == 0:
            return  # Command executed successfully, no need to display output

        spinner.fail("❌")
        # Command failed, print stdout and stderr
        sys.stdout.buffer.write(completed_process.stdout)  # Print stdout
        sys.stderr.buffer.write(completed_process.stderr)  # Print stderr
        exit(1)

    except Exception as e:
            spinner.fail("❌")
            print(f"Error executing command: {str(e)}")
            exit(1)
