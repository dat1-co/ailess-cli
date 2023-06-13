import os
import sys

from .aws_utils import get_regions, get_predefined_instances
import inquirer

def config_prompt():
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

    return answers
