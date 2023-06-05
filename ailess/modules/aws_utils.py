import boto3


def get_regions():
    """Returns a list of all AWS regions"""
    regions = []
    for region in boto3.client("ec2", region_name="us-east-1").describe_regions()["Regions"]:
        regions.append(region['RegionName'])

    regions.sort()
    regions.reverse()

    return regions

def get_predefined_instances():
    return [
        "c6i.large      (2 vCPU, 4 GB RAM)",
        "c6i.xlarge     (4 vCPU, 8 GB RAM)",
        "g4dn.xlarge    (4 vCPU, 16 GB RAM, 1 NVIDIA T4 GPU)",
        "g4dn.12xlarge  (48 vCPU, 192 GB RAM, 4 NVIDIA T4 GPUs)",
        "g4ad.xlarge    (4 vCPU, 16 GB RAM, 1 AMD Radeon Pro V520 GPU)",
        "g4ad.8xlarge   (32 vCPU, 128 GB RAM, 2 AMD Radeon Pro V520 GPUs)",
        "other (custom input)"
    ]
