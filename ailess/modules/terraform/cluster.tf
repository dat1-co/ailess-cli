variable "region" {
  type    = string
}

variable "project_name" {
  type    = string
}

variable "task_port" {
  type    = number
}

variable "instances_count" {
  type    = number
}

variable "instance_type" {
  type    = string
}

variable "task_memory_size" {
  type    = number
}

variable "task_cpu_reservation" {
  type    = number
}

variable "task_num_gpus" {
  type    = number
}

variable "cpu_architecture" {
  type    = string
}

provider "aws" {
  region  = var.region
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Providing a reference to our default VPC
resource "aws_default_vpc" "default_vpc" {
}

terraform {
  backend "s3" {
    bucket = "%AILESS_AWS_ACCOUNT_ID%-ailess-tf-state"
    key    = "%AILESS_PROJECT_NAME%-%AILESS_AWS_REGION%-tf"
    region = "us-east-1"
  }
}

data "aws_availability_zones" "all" {}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [aws_default_vpc.default_vpc.id]
  }
}

data "aws_ami" "ecs" {
  most_recent = true

  filter {
    name   = "name"
    values = [var.task_num_gpus != 0 ? "amzn2-ami-ecs-gpu-*" : "amzn2-ami-ecs-hvm-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }

  filter {
    name   = "architecture"
    values = [var.cpu_architecture]
  }

  owners = ["amazon"]
}

resource "aws_ecs_cluster" "cluster" {
  name = "${var.project_name}-cluster"
}

resource "aws_cloudwatch_log_group" "cluster_log_group" {
  name = "${var.project_name}-cluster-logs"
}

resource "aws_ecs_task_definition" "cluster_task" {
  family                   = "${var.project_name}-cluster-task" # Naming our first task
  container_definitions    = <<DEFINITION
  [
    {
      "name": "${var.project_name}-cluster-task",
      "image": "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/${var.project_name}:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": ${var.task_port},
          "hostPort": 0
        }
      ],
      "memory": ${var.task_memory_size},
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "${var.project_name}-cluster-logs",
          "awslogs-region": "${data.aws_region.current.name}",
          "awslogs-stream-prefix": "streaming"
        }
      }${var.task_num_gpus != 0 ? "," : ""}
      ${var.task_num_gpus != 0 ? "\"resourceRequirements\": [{\"type\":\"GPU\",\"value\":\"${var.task_num_gpus}\"}]" : ""}
    }
  ]
  DEFINITION
  network_mode = "bridge"
  cpu                      = var.task_cpu_reservation
  memory                   = var.task_memory_size
  execution_role_arn       = aws_iam_role.ecsTaskExecutionRole.arn
}

data "local_file" "iam_policy_file" {
  filename = "iam_policy.json"
}

data "aws_iam_policy_document" "assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecsTaskExecutionRole" {
  name_prefix = "${var.project_name}"
  assume_role_policy = "${data.aws_iam_policy_document.assume_role_policy.json}"
}

resource "aws_iam_role_policy_attachment" "ecsTaskExecutionRole_policy" {
  role       = "${aws_iam_role.ecsTaskExecutionRole.name}"
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_alb" "application_load_balancer" {
  name = "${var.project_name}-lb"
  load_balancer_type = "application"
  subnets = data.aws_subnets.default.ids
  security_groups = ["${aws_security_group.load_balancer_security_group.id}"]
}

# Creating a security group for the load balancer:
resource "aws_security_group" "load_balancer_security_group" {
  name_prefix = "${var.project_name}"
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Allowing traffic in from all sources
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb_target_group" "target_group" {
  name = "${var.project_name}-tg"
  port        = var.task_port
  protocol    = "HTTP"
  target_type = "instance"
  vpc_id      = "${aws_default_vpc.default_vpc.id}"
  health_check {
    interval = 10
    healthy_threshold = 2
    unhealthy_threshold = 5
  }
}

resource "aws_lb_listener" "listener" {
  load_balancer_arn = "${aws_alb.application_load_balancer.arn}"
  port              = "80"
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = "${aws_lb_target_group.target_group.arn}"
  }
}

resource "aws_ecs_service" "cluster_service" {
  name = "${var.project_name}_cluster_service"
  cluster         = "${aws_ecs_cluster.cluster.id}"
  task_definition = "${aws_ecs_task_definition.cluster_task.arn}"
  desired_count   = var.instances_count
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent = 200

  load_balancer {
    target_group_arn = "${aws_lb_target_group.target_group.arn}" # Referencing our target group
    container_name   = "${aws_ecs_task_definition.cluster_task.family}"
    container_port   = var.task_port
  }

  capacity_provider_strategy {
    capacity_provider = "${aws_ecs_capacity_provider.capacity_provider.name}"
    weight            = 100
  }

  deployment_circuit_breaker {
    enable = true
    rollback = true
  }

  lifecycle {
    ignore_changes = [
      capacity_provider_strategy,
    ]
  }

  depends_on = [aws_ecs_capacity_provider.capacity_provider]
}


resource "aws_security_group" "service_security_group" {
  name_prefix = "${var.project_name}"
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    security_groups = [aws_security_group.load_balancer_security_group.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}


## ECS

data "aws_iam_policy_document" "ecs_agent" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_agent" {
  name_prefix = "${var.project_name}"
  assume_role_policy = data.aws_iam_policy_document.ecs_agent.json

  dynamic "inline_policy" {
    for_each = jsondecode(data.local_file.iam_policy_file.content).Statement != [] ? ["ecsTaskExecutionRole_policy"] : []
    content {
      name   = inline_policy.key
      policy = data.local_file.iam_policy_file.content
    }
  }
}


resource "aws_iam_role_policy_attachment" "ecs_agent" {
  role       = "${aws_iam_role.ecs_agent.name}"
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_instance_profile" "ecs_agent" {
  name_prefix = "${var.project_name}"
  role = aws_iam_role.ecs_agent.name
  depends_on = [aws_iam_role_policy_attachment.ecs_agent]
}

locals {
  base64_user_data = base64encode("#!/bin/bash\necho ECS_CLUSTER=${aws_ecs_cluster.cluster.name} >> /etc/ecs/ecs.config")
}

resource "aws_launch_template" "ecs_launch_template" {
  name_prefix             = var.project_name
  image_id                = data.aws_ami.ecs.id
  vpc_security_group_ids  = [aws_security_group.service_security_group.id]
  instance_type           = var.instance_type
  disable_api_termination = false
  user_data = local.base64_user_data
  lifecycle {
    create_before_destroy = true
  }
  iam_instance_profile {
    name = aws_iam_instance_profile.ecs_agent.name
  }
}

resource "aws_ecs_capacity_provider" "capacity_provider" {
  name = "${var.project_name}-cluster-capacity-provider"

  auto_scaling_group_provider {
    auto_scaling_group_arn         = aws_autoscaling_group.cluster_asg.arn

    managed_scaling {
      status                    = "ENABLED"
      target_capacity           = 100
    }
  }
}

resource "aws_ecs_cluster_capacity_providers" "capacity_providers" {
  cluster_name = aws_ecs_cluster.cluster.name

  capacity_providers = [aws_ecs_capacity_provider.capacity_provider.name]

  default_capacity_provider_strategy {
    base              = var.instances_count
    weight            = 100
    capacity_provider = aws_ecs_capacity_provider.capacity_provider.name
  }
}

resource "aws_autoscaling_group" "cluster_asg" {
  name_prefix = "${var.project_name}"
  vpc_zone_identifier       = data.aws_subnets.default.ids
  launch_template {
    id      = aws_launch_template.ecs_launch_template.id
    version = "$Latest"
  }
  depends_on = [aws_launch_template.ecs_launch_template]

  desired_capacity          = var.instances_count
  min_size                  = var.instances_count
  max_size                  = "${var.instances_count * 2}"
  health_check_grace_period = 300
  health_check_type         = "EC2"

  lifecycle {
    create_before_destroy = true
    ignore_changes = [
      desired_capacity,
    ]
  }
}
