import json
import os
from string import Template

import boto3
import re
from yaspin import yaspin

from .aws_utils import get_instance_type_info, get_aws_account_id
from .cli_utils import run_command_in_working_directory


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
              .replace("%AILESS_PROJECT_NAME%", convert_to_alphanumeric(config["project_name"]))
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
        project_name=convert_to_alphanumeric(config["project_name"]),
        task_port=config["host_port"],
        task_memory_size=round(instance_data["memory_size"] * 0.9),
        task_cpu_reservation=instance_data["cpu_size"],
        task_num_gpus=instance_data["num_gpus"],
        instance_type=config["ec2_instance_type"],
        instances_count=config["instances_count"]
    )

    with open(".ailess/cluster.tfvars", "w") as tfvars_file:
        tfvars_file.write(tfvars)

def get_tf_state_bucket_name():
    return f"{get_aws_account_id()}-ailess-tf-state"

def ensure_tf_state_bucket_exists():
    s3 = boto3.client('s3', region_name='us-east-1')
    bucket_name = get_tf_state_bucket_name()
    s3.create_bucket(Bucket=bucket_name)

def is_infrastructure_update_required():
    with yaspin(text="    verifying infrastructure") as spinner:
        run_command_in_working_directory("terraform init -reconfigure", spinner, os.path.join(os.getcwd(), ".ailess"))
        output = run_command_in_working_directory("terraform plan -var-file=cluster.tfvars -json", spinner, os.path.join(os.getcwd(), ".ailess"))
        summary_line = filter(lambda line: json.loads(line.decode('utf8')).get("type", "") == "change_summary", output.splitlines())
        changes = json.loads(next(summary_line).decode('utf8'))["changes"]
        spinner.ok("✔")
        return changes["add"] > 0 or changes["change"] > 0 or changes["remove"] > 0

def update_infrastructure():
    with yaspin(text="    updating infrastructure") as spinner:
        run_command_in_working_directory("terraform init -reconfigure", spinner, os.path.join(os.getcwd(), ".ailess"))
        run_command_in_working_directory("terraform apply -auto-approve -var-file=cluster.tfvars", spinner, os.path.join(os.getcwd(), ".ailess"))
        spinner.ok("✔")

def destroy_infrastructure():
    with yaspin(text="    updating infrastructure") as spinner:
        run_command_in_working_directory("terraform destroy -auto-approve -var-file=cluster.tfvars", spinner, os.path.join(os.getcwd(), ".ailess"))
        spinner.ok("✔")
def convert_to_alphanumeric(string):
    # Replace non-alphanumeric characters with hyphens
    alphanumeric_string = re.sub(r'[^a-zA-Z0-9]+', '-', string)
    return alphanumeric_string

