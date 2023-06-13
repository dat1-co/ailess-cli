import os
from string import Template

import boto3

from .aws_utils import get_instance_type_info

def generate_terraform_file(config):
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    tf_template_path = os.path.join(script_dir, 'terraform/cluster.tf')

    with open(tf_template_path, 'r') as file:
        file_contents = file.read()
    with open(".ailess/cluster.tf", "w") as tf_file:
        tf_file.write(
            file_contents
              .replace("%AILESS_AWS_ACCOUNT_ID%", boto3.client('sts').get_caller_identity().get('Account'))
              .replace("%AILESS_PROJECT_NAME%", config["project_name"])
        )


def generate_tfvars_file(config):
    instance_data = get_instance_type_info(config["ec2_instance_type"], config["aws_region"])

    tfvars = Template("""
region = "$region"
project_name = "$project_name"
task_port = $task_port
instance_type = "$instance_type"
instances_count = $instances_count
task_memory_size = $task_memory_size
task_cpu_reservation = $task_cpu_reservation
task_num_gpus = $task_num_gpus
    """).substitute(
        region=config["aws_region"],
        project_name=config["project_name"],
        task_port=config["host_port"],
        task_memory_size=instance_data["memory_size"] * 0.9,
        task_cpu_reservation=instance_data["cpu_size"],
        task_num_gpus=instance_data["num_gpus"],
        instance_type=config["ec2_instance_type"],
        instances_count=config["instances_count"]
    )

    with open(".ailess/cluster.tfvars", "w") as tfvars_file:
        tfvars_file.write(tfvars)
