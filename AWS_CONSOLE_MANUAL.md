# AWS Console Deployment Manual
## Information Retrieval Chatbot - ECS Deployment Guide

This manual provides step-by-step instructions for deploying the Information Retrieval Chatbot application on AWS ECS using the AWS Console. Follow these steps in order.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Step 1: Create S3 Bucket for Data Files](#step-1-create-s3-bucket-for-data-files)
3. [Step 2: Create IAM Role for CodeBuild](#step-2-create-iam-role-for-codebuild)
4. [Step 3: Create CodeBuild Project for Data Processing](#step-3-create-codebuild-project-for-data-processing)
5. [Step 4: Create Amazon ECR Repository](#step-4-create-amazon-ecr-repository)
6. [Step 5: Set Up VPC and Networking](#step-5-set-up-vpc-and-networking)
7. [Step 6: Create Security Groups](#step-6-create-security-groups)
8. [Step 7: Create Application Load Balancer](#step-7-create-application-load-balancer)
9. [Step 8: Create IAM Roles for ECS](#step-8-create-iam-roles-for-ecs)
10. [Step 9: Create ECS Cluster](#step-9-create-ecs-cluster)
11. [Step 10: Create ECS Task Definition](#step-10-create-ecs-task-definition)
12. [Step 11: Create ECS Service](#step-11-create-ecs-service)
13. [Step 12: Verify Deployment](#step-12-verify-deployment)
14. [Step 13: (Optional) Configure HTTPS](#step-13-optional-configure-https)
15. [Troubleshooting](#troubleshooting)
16. [Cost Estimation](#cost-estimation)

---

## Prerequisites

Before starting, ensure you have:

- ✅ AWS Account with administrator access (or appropriate permissions)
- ✅ AWS CLI installed and configured (`aws configure`)
- ✅ Docker installed locally (for building and pushing images)
- ✅ Your code repository accessible (GitHub, CodeCommit, etc.)
- ✅ Basic understanding of AWS services (ECS, ECR, S3, VPC, ALB)

**Note:** Replace `<your-account-id>` and `<your-region>` with your actual AWS account ID and preferred region throughout this guide.

---

## Step 1: Create S3 Bucket for Data Files

**Objective:** Create an S3 bucket to store generated data files from CodeBuild that will be downloaded by ECS tasks at runtime.

**Why:** Centralized storage for data files. S3 is durable, scalable, and cost-effective.

### AWS Console Steps:

1. **Navigate to S3**
   - Open AWS Console → Search for "S3" → Click **S3**

2. **Create Bucket**
   - Click **Create bucket** button
   - **General configuration**:
     - **Bucket name**: `ir-chatbot-data-<your-account-id>`
       - ⚠️ **Important:** S3 bucket names must be globally unique
       - Example: `ir-chatbot-data-123456789012`
     - **AWS Region**: Choose your deployment region (e.g., `us-east-1`)
   
3. **Object Ownership**
   - Select **ACLs disabled (recommended)**
   - Bucket owner enforced

4. **Block Public Access settings**
   - ✅ Keep **all settings enabled** (bucket should be private)
   - Unchecking these is not recommended for this use case

5. **Bucket Versioning**
   - ✅ **Enable** bucket versioning
   - This allows you to track different versions of data files

6. **Default encryption**
   - ✅ **Enable** encryption
   - Encryption type: **Amazon S3 managed keys (SSE-S3)**

7. **Click Create bucket**

8. **Create folder structure**
   - Click on your newly created bucket
   - Click **Create folder**
   - Folder name: `data/`
   - Click **Create folder**

9. **Note the bucket name** - You'll need it for:
   - CodeBuild project environment variables
   - ECS task definition environment variables

---

## Step 2: Create IAM Role for CodeBuild

**Objective:** Create an IAM role that allows CodeBuild to access S3, pull from repository, and run builds.

**Why:** CodeBuild needs permissions to read your source code, install dependencies, and upload artifacts to S3.

### AWS Console Steps:

1. **Navigate to IAM**
   - Open AWS Console → Search for "IAM" → Click **IAM**

2. **Create Role**
   - Click **Roles** in the left sidebar
   - Click **Create role**

3. **Select trusted entity**
   - **Trusted entity type**: Select **AWS service**
   - **Use case**: Select **CodeBuild**
   - Click **Next**

4. **Add permissions**
   - Attach the following managed policies:
     - ✅ `AmazonS3FullAccess` (or create a custom policy for specific bucket access)
     - ✅ `CloudWatchLogsFullAccess`
   - Click **Next**

5. **Name and review**
   - **Role name**: `ir-chatbot-codebuild-role`
   - **Description**: "IAM role for CodeBuild data pipeline project"
   - Click **Create role**

6. **Add inline policy for S3 access** (recommended for security)
   - Click on the role name `ir-chatbot-codebuild-role`
   - Click **Add permissions** → **Create inline policy**
   - Click **JSON** tab
   - Replace with this policy (replace `<your-account-id>` with your actual account ID):
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": [
             "s3:PutObject",
             "s3:GetObject",
             "s3:DeleteObject"
           ],
           "Resource": "arn:aws:s3:::ir-chatbot-data-<your-account-id>/data/*"
         },
         {
           "Effect": "Allow",
           "Action": [
             "s3:ListBucket"
           ],
           "Resource": "arn:aws:s3:::ir-chatbot-data-<your-account-id>"
         }
       ]
     }
     ```
   - Click **Next**
   - Policy name: `S3DataBucketAccess`
   - Click **Create policy**

---

## Step 3: Create CodeBuild Project for Data Processing

**Objective:** Create a CodeBuild project that runs scraping, indexing, and mapping scripts and uploads results to S3.

**Why:** Automates the data generation process. Can be triggered manually when you need to refresh Wikipedia data.

### AWS Console Steps:

1. **Navigate to CodeBuild**
   - Open AWS Console → Search for "CodeBuild" → Click **CodeBuild**

2. **Create Build Project**
   - Click **Build projects** in the left sidebar
   - Click **Create build project**

3. **Project configuration**
   - **Project name**: `ir-chatbot-data-pipeline`
   - **Description**: "Runs Wikipedia scraping, indexing, and document mapping. Uploads results to S3."

4. **Source configuration**
   - **Source provider**: Choose where your code is stored:
     - **GitHub** - If using GitHub
     - **AWS CodeCommit** - If using CodeCommit
     - **S3** - If you want to upload a zip file
   - **Repository**: Select your repository
   - **Branch**: Select branch (e.g., `main`, `master`)
   - **Source version**: Leave as default or specify branch/tag
   - **Buildspec name**: `buildspec.yml` (leave as default if using the provided buildspec)

5. **Environment configuration**
   - **Environment image**: Select **Managed image**
   - **Operating system**: **Ubuntu**
   - **Runtime(s)**: **Standard**
   - **Image**: **aws/codebuild/standard:7.0** (or latest available)
   - **Image version**: **Always use the latest image for this runtime version**
   - **Privileged**: ✅ **Enable** (needed for some dependencies)
   - **Service role**: Select `ir-chatbot-codebuild-role` (created in Step 2)
   - **Compute**: 
     - **Compute type**: **3 GB memory, 2 vCPUs** (recommended for scraping/indexing)
     - **Timeout**: Set to **4 hours** (scraping can take 6-12 hours, but build will timeout before that)

6. **Buildspec**
   - **Use a buildspec file**: ✅ **Yes**
   - **Buildspec name**: `buildspec.yml`
   - **Buildspec override**: Leave empty

7. **Artifacts**
   - **Type**: Select **No artifacts**
   - We upload directly to S3, so no build artifacts needed

8. **Logs**
   - **CloudWatch Logs**: ✅ **Enable**
   - **Group name**: `/aws/codebuild/ir-chatbot-data-pipeline`
   - **Stream name**: Leave blank (auto-generated)

9. **Additional configuration**
   - Click **Additional configuration** to expand
   - **Environment variables**: Click **Add environment variable**
     - **Name**: `S3_BUCKET`
     - **Value**: `ir-chatbot-data-<your-account-id>` (your S3 bucket name from Step 1)
     - **Type**: Plaintext
   - Click **Add environment variable** again:
     - **Name**: `AWS_DEFAULT_REGION`
     - **Value**: `<your-region>` (e.g., `us-east-1`)
     - **Type**: Plaintext
   - (Optional) Click **Add environment variable** again:
     - **Name**: `ARTICLES_PER_TOPIC`
     - **Value**: Number of articles to download per topic (default: `6000`)
     - **Type**: Plaintext
     - **Note**: This overrides the default in buildspec.yml. Lower values (e.g., `1000`) will scrape faster but result in fewer documents.

10. **Click Create build project**

11. **Test the build** (Optional but recommended)
    - Click on the project name `ir-chatbot-data-pipeline`
    - Click **Start build** button
    - **Note:** This build will take 6-12 hours to complete (Wikipedia scraping)
    - Monitor progress in **CloudWatch Logs**
    - After successful build, verify files appear in S3 bucket

---

## Step 4: Create Amazon ECR Repository

**Objective:** Create a private Docker registry to store container images.

**Why:** ECR is AWS's managed Docker registry that integrates seamlessly with ECS.

### AWS Console Steps:

1. **Navigate to ECR**
   - Open AWS Console → Search for "ECR" → Click **Elastic Container Registry**

2. **Create Repository**
   - Click **Repositories** in the left sidebar
   - Click **Create repository**

3. **Repository configuration**
   - **Visibility settings**: Select **Private**
   - **Repository name**: `ir-chatbot`

4. **Tag immutability**
   - ✅ **Enable** tag immutability (recommended for production)
   - Prevents overwriting existing image tags

5. **Scan on push**
   - ✅ **Enable** scan on push
   - Automatically scans images for vulnerabilities

6. **Encryption**
   - **Encryption type**: **AWS managed encryption key (KMS)** (recommended)
   - Or select **Amazon S3 managed encryption key (SSE-S3)**

7. **Click Create repository**

8. **View repository URI**
   - After creation, click on the repository name
   - **Note the repository URI** displayed at the top
   - Example: `123456789012.dkr.ecr.us-east-1.amazonaws.com/ir-chatbot`
   - You'll need this for:
     - Building and pushing Docker images
     - ECS task definition

---

## Step 5: Set Up VPC and Networking

**Objective:** Create a VPC with public and private subnets for ALB and ECS tasks.

**Why:** 
- Public subnets host ALB (needs internet access)
- Private subnets host ECS tasks (more secure)
- NAT Gateway allows ECS tasks to access S3 and internet

### AWS Console Steps:

#### 5.1 Create VPC

1. **Navigate to VPC**
   - Open AWS Console → Search for "VPC" → Click **VPC**

2. **Create VPC**
   - Click **Your VPCs** in the left sidebar
   - Click **Create VPC**

3. **VPC settings**
   - **Name tag**: `ir-chatbot-vpc`
   - **IPv4 CIDR block**: `10.0.0.0/16`
   - **IPv6 CIDR block**: **No IPv6 CIDR block**
   - **Tenancy**: **Default**

4. **Click Create VPC**

#### 5.2 Create Public Subnets (for ALB)

1. **Create first public subnet**
   - Click **Subnets** in the left sidebar
   - Click **Create subnet**
   - **VPC ID**: Select `ir-chatbot-vpc`
   - **Subnet name**: `ir-chatbot-public-subnet-1`
   - **Availability Zone**: Select first AZ (e.g., `us-east-1a`)
   - **IPv4 CIDR block**: `10.0.1.0/24`
   - Click **Create subnet**

2. **Create second public subnet**
   - Click **Create subnet** again
   - **VPC ID**: Select `ir-chatbot-vpc`
   - **Subnet name**: `ir-chatbot-public-subnet-2`
   - **Availability Zone**: Select **different AZ** (e.g., `us-east-1b`)
   - **IPv4 CIDR block**: `10.0.2.0/24`
   - Click **Create subnet**

#### 5.3 Create Private Subnets (for ECS tasks)

1. **Create first private subnet**
   - Click **Create subnet**
   - **VPC ID**: Select `ir-chatbot-vpc`
   - **Subnet name**: `ir-chatbot-private-subnet-1`
   - **Availability Zone**: Select **same AZ as first public subnet** (e.g., `us-east-1a`)
   - **IPv4 CIDR block**: `10.0.11.0/24`
   - Click **Create subnet**

2. **Create second private subnet**
   - Click **Create subnet** again
   - **VPC ID**: Select `ir-chatbot-vpc`
   - **Subnet name**: `ir-chatbot-private-subnet-2`
   - **Availability Zone**: Select **same AZ as second public subnet** (e.g., `us-east-1b`)
   - **IPv4 CIDR block**: `10.0.12.0/24`
   - Click **Create subnet**

#### 5.4 Create Internet Gateway

1. **Create Internet Gateway**
   - Click **Internet gateways** in the left sidebar
   - Click **Create internet gateway**
   - **Name tag**: `ir-chatbot-igw`
   - Click **Create internet gateway**

2. **Attach to VPC**
   - Select the internet gateway you just created
   - Click **Actions** → **Attach to VPC**
   - **Available VPCs**: Select `ir-chatbot-vpc`
   - Click **Attach internet gateway**

#### 5.5 Create NAT Gateway

1. **Allocate Elastic IP**
   - Click **Elastic IPs** in the left sidebar
   - Click **Allocate Elastic IP address**
   - **Network border group**: Select your region
   - Click **Allocate**
   - **Note the Elastic IP allocation ID**

2. **Create NAT Gateway**
   - Click **NAT gateways** in the left sidebar
   - Click **Create NAT gateway**
   - **Name**: `ir-chatbot-nat-gw`
   - **Subnet**: Select `ir-chatbot-public-subnet-1`
   - **Elastic IP allocation ID**: Select the Elastic IP you just allocated
   - Click **Create NAT gateway**
   - ⚠️ **Wait 2-3 minutes** for NAT gateway status to change to "Available"

#### 5.6 Configure Route Tables

1. **Configure public route table**
   - Click **Route tables** in the left sidebar
   - Find the route table automatically created for your VPC
   - Select it and rename to `ir-chatbot-public-rt`:
     - Click **Actions** → **Edit name**
     - Enter name and save
   - Select the route table → Click **Routes** tab → **Edit routes**
   - Click **Add route**:
     - **Destination**: `0.0.0.0/0`
     - **Target**: Select **Internet Gateway** → Select `ir-chatbot-igw`
   - Click **Save changes**
   - Click **Subnet associations** tab → **Edit subnet associations**
   - Select both public subnets:
     - ✅ `ir-chatbot-public-subnet-1`
     - ✅ `ir-chatbot-public-subnet-2`
   - Click **Save associations**

2. **Create private route table**
   - Click **Create route table**
   - **Name tag**: `ir-chatbot-private-rt`
   - **VPC**: Select `ir-chatbot-vpc`
   - Click **Create route table**
   - Select the new route table → Click **Routes** tab → **Edit routes**
   - Click **Add route**:
     - **Destination**: `0.0.0.0/0`
     - **Target**: Select **NAT Gateway** → Select `ir-chatbot-nat-gw`
   - Click **Save changes**
   - Click **Subnet associations** tab → **Edit subnet associations**
   - Select both private subnets:
     - ✅ `ir-chatbot-private-subnet-1`
     - ✅ `ir-chatbot-private-subnet-2`
   - Click **Save associations**

---

## Step 6: Create Security Groups

**Objective:** Configure firewall rules for ALB and ECS tasks.

**Why:** Security groups control inbound/outbound traffic for your resources.

### AWS Console Steps:

#### 6.1 Create ALB Security Group

1. **Navigate to Security Groups**
   - Open AWS Console → Search for "EC2" → Click **EC2**
   - Click **Security Groups** in the left sidebar
   - Click **Create security group**

2. **Basic details**
   - **Security group name**: `ir-chatbot-alb-sg`
   - **Description**: "Security group for Application Load Balancer"
   - **VPC**: Select `ir-chatbot-vpc`

3. **Inbound rules**
   - Click **Add rule**:
     - **Type**: HTTP
     - **Source**: Anywhere-IPv4 (`0.0.0.0/0`)
     - **Description**: "HTTP from internet"
   - Click **Add rule** again:
     - **Type**: HTTPS
     - **Source**: Anywhere-IPv4 (`0.0.0.0/0`)
     - **Description**: "HTTPS from internet"

4. **Outbound rules**
   - Leave default (all traffic)

5. **Click Create security group**

#### 6.2 Create ECS Security Group

1. **Create security group**
   - Click **Create security group**

2. **Basic details**
   - **Security group name**: `ir-chatbot-ecs-sg`
   - **Description**: "Security group for ECS tasks"
   - **VPC**: Select `ir-chatbot-vpc`

3. **Inbound rules**
   - Click **Add rule**:
     - **Type**: Custom TCP
     - **Port range**: `8000`
     - **Source**: Select **Security group** → Select `ir-chatbot-alb-sg`
     - **Description**: "HTTP from ALB"

4. **Outbound rules**
   - Leave default (all traffic)

5. **Click Create security group**

---

## Step 7: Create Application Load Balancer

**Objective:** Create an ALB to distribute traffic and provide a stable endpoint.

**Why:** ALB provides high availability, health checks, and distributes traffic across ECS tasks.

### AWS Console Steps:

1. **Navigate to Load Balancers**
   - Open AWS Console → Search for "EC2" → Click **EC2**
   - Click **Load Balancers** in the left sidebar
   - Click **Create Load Balancer**

2. **Select Load Balancer Type**
   - Select **Application Load Balancer** → Click **Create**

3. **Basic configuration**
   - **Name**: `ir-chatbot-alb`
   - **Scheme**: **Internet-facing**
   - **IP address type**: **IPv4**

4. **Network mapping**
   - **VPC**: Select `ir-chatbot-vpc`
   - **Availability Zones**:
     - ✅ Select both public subnets:
       - `ir-chatbot-public-subnet-1` (us-east-1a)
       - `ir-chatbot-public-subnet-2` (us-east-1b)

5. **Security groups**
   - **Security groups**: Select `ir-chatbot-alb-sg`

6. **Listeners and routing**
   - **Protocol**: HTTP
   - **Port**: 80
   - **Default action**: Click **Create target group** link

7. **Create Target Group** (opens in new page/section)
   - **Target type**: Select **IP addresses**
   - **Target group name**: `ir-chatbot-tg`
   - **Protocol**: HTTP
   - **Port**: 8000
   - **VPC**: Select `ir-chatbot-vpc`
   - **Health check settings**:
     - **Protocol**: HTTP
     - **Path**: `/api/status`
     - **Healthy threshold**: 2
     - **Unhealthy threshold**: 3
     - **Timeout**: 5 seconds
     - **Interval**: 30 seconds
     - **Success codes**: 200
   - Click **Next**
   - **Register targets**: Skip for now (ECS will register automatically)
   - Click **Create target group**

8. **Back to Load Balancer Creation**
   - Return to the load balancer creation page
   - **Default action**: Select the target group `ir-chatbot-tg` you just created

9. **Click Create load balancer**

10. **Wait for ALB to be active**
    - ⚠️ Wait 2-3 minutes for status to change to "Active"
    - Refresh the page if needed

11. **Note the DNS name**
    - Once active, select the load balancer
    - Copy the **DNS name** (e.g., `ir-chatbot-alb-123456789.us-east-1.elb.amazonaws.com`)
    - This is your application's public endpoint

---

## Step 8: Create IAM Roles for ECS

**Objective:** Create IAM roles that allow ECS tasks to download files from S3 and write CloudWatch logs.

**Why:** ECS tasks need permissions to access S3 (data files) and CloudWatch (logging). Two roles are needed: Task Role (for application) and Execution Role (for ECS service).

### AWS Console Steps:

#### 8.1 Create ECS Task Execution Role

1. **Navigate to IAM**
   - Open AWS Console → Search for "IAM" → Click **IAM**

2. **Create Role**
   - Click **Roles** → **Create role**

3. **Select trusted entity**
   - **Trusted entity type**: AWS service
   - **Use case**: Elastic Container Service → **Elastic Container Service Task**
   - Click **Next**

4. **Add permissions**
   - Attach policy: ✅ `AmazonECSTaskExecutionRolePolicy`
   - This provides permissions for ECS to:
     - Pull images from ECR
     - Write logs to CloudWatch
   - Click **Next**

5. **Name and review**
   - **Role name**: `ir-chatbot-ecs-execution-role`
   - **Description**: "ECS task execution role for pulling images and writing logs"
   - Click **Create role**

#### 8.2 Create ECS Task Role

1. **Create Role**
   - Click **Create role**

2. **Select trusted entity**
   - **Trusted entity type**: AWS service
   - **Use case**: Elastic Container Service → **Elastic Container Service Task**
   - Click **Next**

3. **Add permissions**
   - **Skip permissions** for now (we'll add inline policy)
   - Click **Next**

4. **Name and review**
   - **Role name**: `ir-chatbot-ecs-task-role`
   - **Description**: "ECS task role for application access to S3 and CloudWatch"
   - Click **Create role**

5. **Add inline policy for S3 access**
   - Click on the role name `ir-chatbot-ecs-task-role`
   - Click **Add permissions** → **Create inline policy**
   - Click **JSON** tab
   - Replace with this policy (replace `<your-account-id>` with your account ID):
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": [
             "s3:GetObject"
           ],
           "Resource": "arn:aws:s3:::ir-chatbot-data-<your-account-id>/data/*"
         },
         {
           "Effect": "Allow",
           "Action": [
             "s3:ListBucket"
           ],
           "Resource": "arn:aws:s3:::ir-chatbot-data-<your-account-id>"
         }
       ]
     }
     ```
   - Click **Next**
   - **Policy name**: `S3DataBucketReadAccess`
   - Click **Create policy**

---

## Step 9: Create ECS Cluster

**Objective:** Create an ECS cluster to host your tasks.

**Why:** Clusters are logical groupings of tasks/services. With Fargate, AWS manages the infrastructure.

### AWS Console Steps:

1. **Navigate to ECS**
   - Open AWS Console → Search for "ECS" → Click **Elastic Container Service**

2. **Create Cluster**
   - Click **Clusters** in the left sidebar
   - Click **Create cluster**

3. **Cluster configuration**
   - **Cluster name**: `ir-chatbot-cluster`
   - **Infrastructure**: Select **AWS Fargate (serverless)**

4. **Click Create**

5. **Wait for cluster creation**
   - Cluster will be created immediately (Fargate is serverless)

---

## Step 10: Create ECS Task Definition

**Objective:** Define container configuration, resource requirements, and environment variables.

**Why:** Task definition is a blueprint that tells ECS how to run your container.

### AWS Console Steps:

1. **Navigate to Task Definitions**
   - In ECS console, click **Task Definitions** in the left sidebar
   - Click **Create new Task Definition**

2. **Task definition configuration**
   - **Family**: `ir-chatbot-task`
   - **Launch type**: **Fargate**
   - **Operating system/Architecture**: **Linux/X86_64**
   - **Task size**:
     - **CPU**: `2 vCPU` (minimum for ML models)
     - **Memory**: `8 GB` (sufficient for BlenderBot + BART models)

3. **Container definitions**
   - Click **Add container**

4. **Container configuration**
   - **Container name**: `ir-chatbot-container`
   - **Image URI**: Enter your ECR repository URI + `:latest`
     - Example: `123456789012.dkr.ecr.us-east-1.amazonaws.com/ir-chatbot:latest`
   - **Essential container**: ✅ Yes

5. **Port mappings**
   - **Container port**: `8000`
   - **Protocol**: `TCP`
   - **App protocol**: `HTTP`

6. **Environment variables**
   - Click **Add environment variable**:
     - **Key**: `FORCE_CPU`
     - **Value**: `1`
   - Click **Add environment variable**:
     - **Key**: `PYTHONUNBUFFERED`
     - **Value**: `1`
   - Click **Add environment variable**:
     - **Key**: `AWS_DEFAULT_REGION`
     - **Value**: `<your-region>` (e.g., `us-east-1`)
   - Click **Add environment variable**:
     - **Key**: `S3_BUCKET`
     - **Value**: `ir-chatbot-data-<your-account-id>` (your S3 bucket name)
   - Click **Add environment variable**:
     - **Key**: `S3_DATA_PREFIX`
     - **Value**: `data/`

7. **Health check**
   - **Health check**: ✅ Enable
   - **Command**: `CMD-SHELL,curl -f http://localhost:8000/api/status || exit 1`
   - **Interval**: 30 seconds
   - **Timeout**: 5 seconds
   - **Start period**: **600 seconds** (10 minutes - allow time for S3 download + model loading)
   - **Retries**: 3

8. **Logging**
   - **Log driver**: Select **awslogs**
   - **Log group**: `/ecs/ir-chatbot`
   - ✅ **Create log group if it doesn't exist**
   - **Log stream prefix**: `ecs`

9. **Click Add** to finish container configuration

10. **Task execution role**
    - **Task execution role**: Select `ir-chatbot-ecs-execution-role`

11. **Task role**
    - **Task role**: Select `ir-chatbot-ecs-task-role`

12. **Click Create** to create the task definition

---

## Step 11: Create ECS Service

**Objective:** Create a service to run and maintain desired number of tasks.

**Why:** Services ensure your application is always running and can handle traffic spikes.

### AWS Console Steps:

1. **Navigate to Cluster**
   - In ECS console, click **Clusters** → Click `ir-chatbot-cluster`
   - Click **Services** tab
   - Click **Create**

2. **Compute configuration**
   - **Launch type**: **Fargate**
   - **Task Definition**:
     - **Family**: `ir-chatbot-task`
     - **Revision**: `latest` (or select the revision you just created)
   - **Platform version**: **Latest**
   - **Cluster VPC**: Select `ir-chatbot-vpc`
   - **Subnets**: Select both private subnets:
     - ✅ `ir-chatbot-private-subnet-1`
     - ✅ `ir-chatbot-private-subnet-2`
   - **Security group**: Select `ir-chatbot-ecs-sg`
   - **Auto-assign public IP**: **DISABLED** (tasks use NAT Gateway for internet access)

3. **Load balancing**
   - **Load balancer type**: **Application Load Balancer**
   - **Load balancer name**: Select `ir-chatbot-alb`
   - **Container to load balance**: 
     - Select `ir-chatbot-container:8000`
   - **Target group name**: Select `ir-chatbot-tg`
   - **Production listener**: Port 80, Protocol HTTP
   - **Health check grace period**: **600 seconds** (10 minutes)

4. **Service auto scaling**
   - **Do not adjust the service's desired count**: Selected (start with 1 task)
   - You can enable auto-scaling later if needed

5. **Deployment configuration**
   - **Deployment type**: **Rolling update**
   - **Minimum healthy percent**: 100
   - **Maximum percent**: 200

6. **Click Create**

7. **Wait for service to stabilize**
    - ⚠️ This will take **5-15 minutes**:
      - Task starts pulling image from ECR (~2-3 minutes)
      - Downloads data files from S3 (~1-2 minutes)
      - Loads ML models (~3-5 minutes)
      - Passes health checks
    - Monitor progress in:
      - **ECS Service** → **Tasks** tab → View task status
      - **CloudWatch Logs** → `/ecs/ir-chatbot`

---

## Step 12: Verify Deployment

**Objective:** Test the application through the load balancer.

### AWS Console Steps:

1. **Get Load Balancer DNS Name**
   - Navigate to **EC2** → **Load Balancers**
   - Select `ir-chatbot-alb`
   - Copy the **DNS name** (e.g., `ir-chatbot-alb-123456789.us-east-1.elb.amazonaws.com`)

2. **Check Task Status**
   - Navigate to **ECS** → **Clusters** → `ir-chatbot-cluster` → **Services** → `ir-chatbot-service`
   - Click **Tasks** tab
   - Wait for task status to be **RUNNING**
   - Click on the task ID to view details
   - Check **Health status** (should show "Healthy" after health checks pass)

3. **Access Application**
   - Open browser
   - Navigate to: `http://<ALB_DNS_NAME>`
   - Wait for application to load (first load may take time while models initialize)
   - You should see the chatbot interface

4. **Test Functionality**
   - Try chit-chat mode (default)
   - Select a topic and try a query
   - Verify responses are working

5. **Check Logs** (if issues)
   - Navigate to **CloudWatch** → **Log groups**
   - Select `/ecs/ir-chatbot`
   - View latest log streams
   - Check for errors or warnings

---

## Step 13: (Optional) Configure HTTPS

**Objective:** Add SSL certificate for secure HTTPS access.

### Prerequisites:
- A domain name pointing to your ALB (via Route 53 or external DNS)

### AWS Console Steps:

1. **Request SSL Certificate**
   - Navigate to **Certificate Manager (ACM)**
   - Click **Request a certificate**
   - **Certificate type**: **Request a public certificate**
   - **Domain name**: Enter your domain (e.g., `chatbot.example.com`)
   - **Validation method**: **DNS validation** (recommended)
   - Click **Request**
   - Complete DNS validation steps (add CNAME records to your DNS)

2. **Wait for Certificate Validation**
   - Certificate status will change to "Issued" after validation

3. **Update Load Balancer Listener**
   - Navigate to **EC2** → **Load Balancers** → Select `ir-chatbot-alb`
   - Click **Listeners** tab → **Add listener**
   - **Protocol**: HTTPS
   - **Port**: 443
   - **Default SSL certificate**: Select your ACM certificate
   - **Default action**: Forward to `ir-chatbot-tg`
   - Click **Add**

4. **Redirect HTTP to HTTPS** (Optional but recommended)
   - Select HTTP listener (port 80)
   - Click **Edit**
   - **Default action**: Change to **Redirect to URL**
   - **Protocol**: HTTPS
   - **Port**: 443
   - **Status code**: 301 - Permanently moved
   - Click **Save changes**

5. **Test HTTPS**
   - Access application via: `https://your-domain.com`
   - Verify SSL certificate is valid

---

## Troubleshooting

### Tasks Failing to Start

**Symptoms:** Tasks show as "STOPPED" or fail immediately.

**Solutions:**
- Check CloudWatch logs: `/ecs/ir-chatbot`
- Verify ECR image URI is correct in task definition
- Check IAM roles are properly attached (execution role and task role)
- Verify security groups allow necessary traffic
- Check task definition resource limits (CPU/memory)

### Health Checks Failing

**Symptoms:** Tasks run but health check shows "Unhealthy".

**Solutions:**
- Increase health check grace period (currently 600 seconds)
- Verify `/api/status` endpoint is working in logs
- Check if data files downloaded successfully from S3
- Verify models loaded successfully
- Check container logs for errors

### 502 Bad Gateway Errors

**Symptoms:** ALB returns 502 errors when accessing application.

**Solutions:**
- Verify security group `ir-chatbot-ecs-sg` allows traffic from `ir-chatbot-alb-sg` on port 8000
- Check target group shows healthy targets
- Verify tasks are running and passing health checks
- Check CloudWatch logs for application errors

### S3 Access Denied Errors

**Symptoms:** Container fails to download data files from S3.

**Solutions:**
- Verify ECS task role (`ir-chatbot-ecs-task-role`) has S3 GetObject permission
- Check S3 bucket name in environment variables matches actual bucket
- Verify S3 bucket policy allows access (if using bucket policy)
- Check IAM policy resource ARN matches bucket name

### Slow Startup Times

**Symptoms:** Application takes 10+ minutes to become available.

**Solutions:**
- This is normal for first startup:
  - Image pull: 2-3 minutes
  - S3 download: 1-2 minutes
  - Model download: 3-5 minutes
  - Total: 6-10 minutes
- Subsequent starts are faster if using same task
- Consider increasing health check grace period

### Models Not Loading

**Symptoms:** Application starts but models fail to load.

**Solutions:**
- Check CloudWatch logs for model download errors
- Verify internet access through NAT Gateway
- Check disk space (models require ~2-3GB)
- Verify FORCE_CPU environment variable is set correctly

---

## Cost Estimation

### Monthly Costs (Approximate, running 24/7)

- **ECS Fargate**: 
  - 2 vCPU: ~$0.04/vCPU-hour × 2 = $0.08/hour
  - 8 GB Memory: ~$0.004/GB-hour × 8 = $0.032/hour
  - Total: ~$0.112/hour × 730 hours = **~$82/month**

- **NAT Gateway**: 
  - ~$0.045/hour × 730 hours = **~$33/month**

- **Application Load Balancer**: 
  - ~$0.0225/hour × 730 hours = **~$16/month**

- **S3 Storage**: 
  - Data files (~10MB): Negligible (~$0.0002/month)
  - Requests: Minimal

- **ECR Storage**: 
  - Image (~3-4GB): ~$0.10/GB/month = **~$0.40/month**

- **CloudWatch Logs**: 
  - First 5GB free, then ~$0.50/GB

- **CodeBuild**: 
  - First 100 build minutes/month free
  - Then ~$0.005/minute

**Estimated Total: ~$130-140/month** (24/7 operation)

### Cost Optimization Tips

1. **Use Auto Scaling**: Scale down during low-traffic periods
2. **Use Scheduled Scaling**: Stop tasks during non-business hours
3. **Use Spot Instances**: Not available for Fargate, but consider EC2 launch type
4. **Optimize Image Size**: Multi-stage builds help reduce image size
5. **Monitor Costs**: Set up AWS Budgets and Cost Alerts

---

## Next Steps

After successful deployment:

1. ✅ **Set up monitoring**: Configure CloudWatch alarms for CPU, memory, and health checks
2. ✅ **Enable auto-scaling**: Configure automatic scaling based on CPU/memory usage
3. ✅ **Set up CI/CD**: Automate Docker image builds and deployments
4. ✅ **Configure domain**: Point your domain to the load balancer
5. ✅ **Enable HTTPS**: Follow Step 13 to add SSL certificate
6. ✅ **Regular data updates**: Schedule CodeBuild runs to refresh Wikipedia data

---

## Support and Resources

- **AWS ECS Documentation**: https://docs.aws.amazon.com/ecs/
- **AWS Fargate Pricing**: https://aws.amazon.com/fargate/pricing/
- **CloudWatch Logs**: Monitor application logs in real-time
- **AWS Support**: Contact AWS Support for account/billing issues

---

**Last Updated:** 2024
**Version:** 1.0

