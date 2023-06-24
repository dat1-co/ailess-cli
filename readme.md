# ailess - Easily deploy your machine learning models as endpoints on AWS

ailess is a Python package that allows you to easily deploy your machine learning models and turn them into an endpoint on AWS.

## Features

- **No DevOps Degree required**: ailess is designed to be used by data scientists and machine learning engineers with no prior experience in DevOps while following best DevOps practices.
- **Solid Pipeline**: ailess packages your model and its dependencies into a Docker image, pushes it to AWS ECR, and deploys it as an endpoint on AWS ECS.
- **Easy to use**: ailess is designed to be used with a single command line interface.

## Getting Started

### Pre-requisites

- [Python 3.6+](https://www.python.org/downloads/)
- [Docker](https://docs.docker.com/get-docker/)
- [Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli)
- [AWS Account](https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account/)

### Installation

```bash
pip install ailess
```

## Usage

### Initialize project with ailess

To initialize ailess in your project, run the following command in your project's root directory:
```bash
ailess init
```
You will be prompted to select the AWS Region you want to deploy your model to, instance type, and port number etc.
In turn, ailess will generate the following files in .ailess directory:

- **.ailess/config.json**: Configuration file for ailess.
- **.ailess/Dockerfile**: Dockerfile for building the Docker image.
- **.ailess/cluster.tf**: Terraform configuration file for creating the ECS cluster.
- **.ailess/cluster.tfvars**: Terraform variables file for creating the ECS cluster.
- **requirements.txt**: Python dependencies for your model.

### Deploy your model

To deploy your model, run the following command in your project's root directory:
```bash
ailess deploy
```
This will build the Docker image, push it to AWS ECR, create infrastrcuture, and deploy it as an endpoint on AWS ECS.
When the deployment is complete, you will see the endpoint URL in the output.

When you want to update your model, run the same command again. 
This will update the Docker image, push it to AWS ECR, and update the endpoint on AWS ECS. 
On each run of the `deploy` command ailess will verify that the infrastructure is up-to-date and only update it if necessary.

### Remove your model

To delete the infrastructure, run the following command in your project's root directory:
```bash
ailess destroy
```

This will delete the infrastructure and the endpoint on AWS ECS.

## How it works

### Docker Image

ailess packages your model and its dependencies into a Docker image. It will try to detect a correct version and install CUDA and cuDNN if needed.

### Cluster

ailess creates an ECS cluster that sits behind an Application Load Balancer (ALB).
This allows zero-downtime deployment and auto-scaling of the endpoint.
The ECS also runs health checks on the endpoint and restarts the container if it fails.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
