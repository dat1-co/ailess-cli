import base64
import time

import boto3
from yaspin import yaspin

from ailess.modules.cli_utils import run_command_in_working_directory
from ailess.modules.docker_utils import (
    login_to_docker_registry,
    DOCKER_ARCHITECTURE_AMD64,
    DOCKER_ARCHITECTURE_ARM64,
)


def sort_key(region):
    # Assign priority based on region category
    if region.startswith("us"):
        return "a"  # us regions come first
    elif region.startswith("eu"):
        return "b"  # eu regions come next
    elif region.startswith("ap"):
        return "c"  # ap regions come after eu
    elif region.startswith("ca"):
        return "d"  # ca regions come after ap
    elif region.startswith("sa"):
        return "e"  # sa regions come after ca

    # If none of the above categories match, assign a lower priority
    return "z"


def get_regions():
    """Returns a list of all AWS regions"""
    regions = []
    for region in boto3.client("ec2", region_name="us-east-1").describe_regions()["Regions"]:
        regions.append(region["RegionName"])

    ## Sort regions us, eu, ap, ca, sa
    sorted_regions = sorted(regions, key=lambda r: (sort_key(r), r))

    return sorted_regions


def get_predefined_instances():
    return [
        "t3.small       (2 vCPU, 2 GB RAM)",
        "t3.xlarge      (4 vCPU, 16 GB RAM)",
        "g4dn.xlarge    (4 vCPU, 16 GB RAM, 1 NVIDIA T4 GPU)",
        "g4dn.12xlarge  (48 vCPU, 192 GB RAM, 4 NVIDIA T4 GPUs)",
        "g4ad.xlarge    (4 vCPU, 16 GB RAM, 1 AMD Radeon Pro V520 GPU)",
        "g4ad.8xlarge   (32 vCPU, 128 GB RAM, 2 AMD Radeon Pro V520 GPUs)",
        "other (custom input)",
    ]


def get_instance_type_info(instance_type: str, region: str):
    response = boto3.client("ec2", region_name=region).describe_instance_types(
        DryRun=False,
        InstanceTypes=[instance_type],
    )

    if len(response["InstanceTypes"]) == 0:
        print(f"ERROR: {instance_type} is not a valid instance type in {region}")
        exit(1)

    arch = DOCKER_ARCHITECTURE_AMD64

    if "arm64" in response["InstanceTypes"][0]["ProcessorInfo"]["SupportedArchitectures"]:
        arch = DOCKER_ARCHITECTURE_ARM64

    return {
        "memory_size": response["InstanceTypes"][0]["MemoryInfo"]["SizeInMiB"],
        "cpu_size": response["InstanceTypes"][0]["VCpuInfo"]["DefaultVCpus"] * 1024,
        "num_gpus": len(response["InstanceTypes"][0].get("GpuInfo", {}).get("Gpus", [])),
        "cpu_architecture": arch,
    }


def get_aws_account_id():
    return boto3.client("sts").get_caller_identity().get("Account")


def ensure_ecr_repo_exists(config):
    ecr_client = boto3.client("ecr", region_name=config["aws_region"])
    project_name = config["project_name"]
    try:
        ecr_client.create_repository(repositoryName=project_name)
    except ecr_client.exceptions.RepositoryAlreadyExistsException:
        pass  # Repo already exists
    except Exception as e:
        print(f"Error ensuring ECR repository exists: {e}")
        exit(1)


def push_docker_image(config):
    from ailess.modules.terraform_utils import convert_to_alphanumeric

    with yaspin(text="    pushing docker image") as spinner:
        ensure_ecr_repo_exists(config)
        ecr_token = boto3.client("ecr", region_name=config["aws_region"]).get_authorization_token()[
            "authorizationData"
        ][0]["authorizationToken"]
        decoded_string = base64.b64decode(ecr_token).decode("utf-8")
        ecr_password = decoded_string.split(":")[1]
        # Login to ECR
        login_to_docker_registry(
            "AWS",
            ecr_password,
            f"{get_aws_account_id()}.dkr.ecr.{config['aws_region']}.amazonaws.com",
            spinner,
        )

        ecr_image_name = f"{get_aws_account_id()}.dkr.ecr.{config['aws_region']}.amazonaws.com/{convert_to_alphanumeric(config['project_name'])}"

        run_command_in_working_directory(
            f"docker tag {convert_to_alphanumeric(config['project_name'])} {ecr_image_name}", spinner
        )
        run_command_in_working_directory(f"docker push {ecr_image_name}", spinner)
        spinner.ok("✔")


def ecs_deploy(config):
    ecs_client = boto3.client("ecs", region_name=config["aws_region"])

    cluster_name = f"{config['project_name']}-cluster"
    service_name = f"{config['project_name']}_cluster_service"
    with yaspin(text="    deploying new code") as spinner:
        ecs_client.update_service(cluster=cluster_name, service=service_name, forceNewDeployment=True)
        spinner.ok("✔")


def print_endpoint_info(config):
    from ailess.modules.terraform_utils import convert_to_alphanumeric

    elbv2_client = boto3.client("elbv2", region_name=config["aws_region"])
    alb_name = f"{convert_to_alphanumeric(config['project_name'])}-lb"

    # Describe the load balancers with the given name
    response = elbv2_client.describe_load_balancers(Names=[alb_name])

    # Extract the public DNS name from the response
    alb_dns_name = response["LoadBalancers"][0]["DNSName"]
    print(f"🌐    endpoint: http://{alb_dns_name}")


def get_latest_deployment(cluster_name, service_name, region):
    ecs_client = boto3.client("ecs", region_name=region)

    response = ecs_client.describe_services(cluster=cluster_name, services=[service_name])
    services = response["services"]

    if services:
        service = services[0]
        deployments = service.get("deployments", [])
        if deployments:
            latest_deployment = max(deployments, key=lambda d: d["createdAt"])
            return latest_deployment

    return None


def wait_for_deployment(config):
    cluster_name = f"{config['project_name']}-cluster"
    service_name = f"{config['project_name']}_cluster_service"
    with yaspin(text="    waiting for deployment") as spinner:
        latest_deployment = get_latest_deployment(cluster_name, service_name, config["aws_region"])
        if latest_deployment:
            while latest_deployment["rolloutState"] != "COMPLETED":
                time.sleep(5)
                latest_deployment = get_latest_deployment(cluster_name, service_name, config["aws_region"])
                if latest_deployment["rolloutState"] == "FAILED":
                    spinner.fail("❌")
                    print(f"Deployment failed {latest_deployment['rolloutStateReason']}, more details here:")
                    print(
                        f"https://console.aws.amazon.com/ecs/home?region={config['aws_region']}#/clusters/{cluster_name}/services/{service_name}/events"
                    )
                    exit(1)
            spinner.ok("✔")
        else:
            spinner.fail("❌")
