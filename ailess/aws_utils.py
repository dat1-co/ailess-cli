import boto3


def get_regions():
    """Returns a list of all AWS regions"""
    regions = []
    for region in boto3.client("ec2", region_name="us-east-1").describe_regions()["Regions"]:
        regions.append(region['RegionName'])
    return regions
