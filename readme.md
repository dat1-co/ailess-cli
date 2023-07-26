# Ailess - Easily deploy your machine learning models as endpoints on AWS

Ailess is a Python package that allows you to easily deploy your machine learning models and turn them into an endpoint on AWS.

## Features

- **No DevOps Degree required**: Ailess is designed to be used by data scientists and machine learning engineers with no prior experience in DevOps while following best DevOps practices.
- **Solid Pipeline**: Ailess packages your model and its dependencies into a Docker image, pushes it to AWS ECR, and deploys it as an endpoint on AWS ECS.
- **Zero downtime deployment**: Ailess uses AWS ECS to deploy your model as an endpoint behind an Application Load Balancer (ALB). This allows zero-downtime deployment and auto-scaling of the cluster.
- **Auto-recovery**: Ailess runs health checks on the endpoint and restarts the container if it fails or rolls the deployment back if it fails to start.

## Getting Started

### Pre-requisites

- [Python 3.6+](https://www.python.org/downloads/)
- [Docker](https://docs.docker.com/get-docker/)
- [Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli)
- [AWS Account](https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account/)
- AWS Credentials configured via ~/.aws/credentials or environment variables
- Health check endpoint in your app. Load Balancer will be sending a GET request to `/` and expect a 200 response code.

### Installation

```bash
pip install ailess
```

## Usage

### Initialize project with Ailess

To initialize Ailess in your project, run the following command in your project's root directory:
```bash
ailess init
```
You will be prompted to select the AWS Region you want to deploy your model to, instance type, and port number etc.
In turn, Ailess will generate the following files in .ailess directory:

- **.ailess/config.json**: Configuration file for ailess.
- **Dockerfile**: Dockerfile for building the Docker image.
- **docker-compose.yml**: Docker Compose file for running the Docker image locally.
- **.ailess/iam_policy.json**: IAM policy for the ECS task.
- **.ailess/cluster.tf**: Terraform configuration file for creating the ECS cluster.
- **.ailess/cluster.tfvars**: Terraform variables file for creating the ECS cluster.
- **requirements.txt**: Python dependencies for your model.

All of these files can be modified to suit your needs and Ailess will continue to work and appropriately update the infrastructure/docker image.

### Running locally

To run your model locally, run the following command in your project's root directory:
```bash
ailess serve
```

This will build the Docker image and run it locally.

### Deploy your model

To deploy your model, run the following command in your project's root directory:
```bash
ailess deploy
```
This will build the Docker image, push it to AWS ECR, create infrastrcuture, and deploy it as an endpoint on AWS ECS.
When the deployment is complete, you will see the endpoint URL in the output.

When you want to update your model, run the same command again. 
This will update the Docker image, push it to AWS ECR, and update the endpoint on AWS ECS. 
On each run of the `deploy` command Ailess will verify that the infrastructure is up-to-date and only update it if necessary.

### Remove your model

To delete the infrastructure, run the following command in your project's root directory:
```bash
ailess destroy
```

This will delete the infrastructure and the endpoint on AWS ECS.

## How it works

### Docker Image

Ailess packages your model and its dependencies into a Docker image. It will try to detect a correct version and install CUDA and cuDNN if needed.

### Cluster

Ailess creates an ECS cluster that sits behind an Application Load Balancer (ALB).
This allows zero-downtime deployment and auto-scaling of the cluster.
The ECS also runs health checks on the endpoint and restarts the container if it fails or rolls the deployment back if it fails to start.

## Configuration

### Accessing AWS resources

By default, your app will have no access to AWS resources. 
To allow your app to access AWS resources, edit the .ailess/iam_policy.json file and add the necessary permissions.
The easiest way to do this is to use the [IAM Policy Generator](https://awspolicygen.s3.amazonaws.com/policygen.html) with IAM Policy type.

To allow your app to access AWS resources while running locally with `ailess serve`, you will need to modify the docker-compose.yml file.

If your credentials are stored in ~/.aws/credentials, you can mount the credentials file to the container:
```diff
services:
  ailess-test-project:
    environment:
      - PYTHONUNBUFFERED=1
    image: ailess-test-project:latest
    build: .
    platform: linux/amd64
    ports:
      - "5000:5000"  
+   volumes:
+     - $HOME/.aws/credentials:/root/.aws/credentials:ro
```

If your credentials are stored in environment variables, you can pass them to the container:
```diff
services:
  ailess-test-project:
    environment:
      - PYTHONUNBUFFERED=1
+     - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
+     - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
+     - AWS_REGION=${AWS_REGION}
    image: ailess-test-project:latest
    build: .
    platform: linux/amd64
    ports:
      - "5000:5000"  
```

## Examples

[Examples repository](https://github.com/dat1-co/ailess-examples) contains several projects deployable with Ailess showcasing different use cases.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
