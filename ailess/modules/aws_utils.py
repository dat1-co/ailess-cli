import boto3

def sort_key(region):
    # Assign priority based on region category
    if region.startswith('us'):
        return 'a'  # us regions come first
    elif region.startswith('eu'):
        return 'b'  # eu regions come next
    elif region.startswith('ap'):
        return 'c'  # ap regions come after eu
    elif region.startswith('ca'):
        return 'd'  # ca regions come after ap
    elif region.startswith('sa'):
        return 'e'  # sa regions come after ca

    # If none of the above categories match, assign a lower priority
    return 'z'
def get_regions():
    """Returns a list of all AWS regions"""
    regions = []
    for region in boto3.client("ec2", region_name="us-east-1").describe_regions()["Regions"]:
        regions.append(region['RegionName'])

    ## Sort regions us, eu, ap, ca, sa
    sorted_regions = sorted(regions, key=lambda r: (sort_key(r), r))

    return sorted_regions

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

def get_instance_type_info(instance_type: str, region: str):
    response = boto3.client("ec2", region_name=region).describe_instance_types(
        DryRun=False,
        InstanceTypes=[instance_type],
    )

    if len(response['InstanceTypes']) == 0:
        print(f"ERROR: {instance_type} is not a valid instance type in {region}")
        exit(1)

    return {
        "memory_size": response['InstanceTypes'][0]['MemoryInfo']['SizeInMiB'],
        "cpu_size": response['InstanceTypes'][0]['VCpuInfo']['DefaultVCpus'] * 1024,
        "num_gpus": len(response['InstanceTypes'][0].get('GpuInfo', {}).get('Gpus', [])),
    }
