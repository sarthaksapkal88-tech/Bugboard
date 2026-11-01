# BugBoard — Cloud-Native Issue Tracker

> **CSA3004 Cloud Native Orchestration — End-to-End Deployment on Amazon EKS**
>
> **Student:** Sarthak Sapkal | **PRN:** 20240801015 | **University:** DYPIU, Pune

---

## Table of Contents

1. [About the Project](#about-the-project)
2. [Features](#features)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Prerequisites](#prerequisites)
6. [Step-by-Step Deployment Guide](#step-by-step-deployment-guide)
   - [Step 1 — Set Up EC2 Environment](#step-1--set-up-ec2-environment)
   - [Step 2 — Clone the Repository](#step-2--clone-the-repository)
   - [Step 3 — Build and Test Docker Image](#step-3--build-and-test-docker-image)
   - [Step 4 — Create Amazon ECR Repository and Push Image](#step-4--create-amazon-ecr-repository-and-push-image)
   - [Step 5 — Create Amazon EKS Cluster](#step-5--create-amazon-eks-cluster)
   - [Step 6 — Deploy to EKS](#step-6--deploy-to-eks)
   - [Step 7 — Set Up GitHub Actions CI/CD with OIDC](#step-7--set-up-github-actions-cicd-with-oidc)
   - [Step 8 — Install and Configure Argo CD](#step-8--install-and-configure-argo-cd)
7. [Architecture Diagram](#architecture-diagram)
8. [Viva Preparation — Key Concepts](#viva-preparation--key-concepts)

---

## About the Project

**BugBoard** is a lightweight issue/bug tracker web application built with Python Flask. It allows teams to create, edit, filter, search, and delete issues — each with a priority level and status. The application is containerized with Docker, deployed on Amazon EKS (Elastic Kubernetes Service), and uses a full CI/CD pipeline with GitHub Actions (OIDC authentication) and Argo CD (GitOps).

---

## Features

1. **Issue Management** — Create, edit, and delete issues with title, description, priority (Low/Medium/High/Critical), and status (Open/In Progress/Resolved/Closed).
2. **Dashboard with Stats** — View total issues, open issues, in-progress, and resolved/closed counts at a glance.
3. **Filtering & Search** — Filter issues by status, priority, and free-text search across titles and descriptions.
4. **Health Check Endpoint** — `/health` endpoint returns JSON for Kubernetes liveness and readiness probes.
5. **Responsive Design** — Works on desktop and mobile.

---

## Tech Stack

| Layer            | Technology                                 |
|------------------|--------------------------------------------|
| **Application**  | Python 3.11, Flask, Gunicorn, SQLite       |
| **Container**    | Docker                                     |
| **Registry**     | Amazon ECR                                 |
| **Orchestration**| Amazon EKS (Kubernetes)                    |
| **CI/CD**        | GitHub Actions with OIDC authentication    |
| **GitOps**       | Argo CD with automated sync                |
| **Infrastructure**| AWS EC2 (Ubuntu), eksctl, kubectl, AWS CLI |

---

## Project Structure

```
bugboard/
├── app.py                          # Flask application (main)
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Container build instructions
├── .dockerignore                   # Files excluded from Docker build
├── templates/
│   ├── base.html                   # Base layout template
│   ├── index.html                  # Dashboard page
│   ├── create.html                 # Create issue form
│   └── edit.html                   # Edit issue form
├── static/
│   └── style.css                   # Application styling
├── tests/
│   └── test_app.py                 # Unit tests (16 tests)
├── k8s/
│   ├── deployment.yaml             # Kubernetes Deployment manifest
│   └── service.yaml                # Kubernetes Service manifest (LoadBalancer)
├── .github/
│   └── workflows/
│       └── ci-cd.yaml              # GitHub Actions CI/CD pipeline
├── argocd/
│   └── application.yaml            # Argo CD Application config
└── README.md                       # This file
```

---

## Prerequisites

- AWS account with permissions for EC2, ECR, EKS, IAM
- GitHub account
- An EC2 instance running Ubuntu (t3.small or larger, 20 GB storage)
- Docker, AWS CLI, eksctl, and kubectl installed on the EC2 instance

---

## Step-by-Step Deployment Guide

### Step 1 — Set Up EC2 Environment

1. **Launch an EC2 instance** — Ubuntu 22.04, instance type `t3.small`, storage **20 GB**, security group allowing SSH (22), HTTP (80), and port 5000.

2. **SSH into the instance:**
   ```bash
   ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>
   ```

3. **Install Docker:**
   ```bash
   sudo apt update
   sudo apt install -y docker.io
   sudo usermod -aG docker $USER
   newgrp docker
   docker --version
   ```

4. **Install AWS CLI:**
   ```bash
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   sudo apt install -y unzip
   unzip awscliv2.zip
   sudo ./aws/install
   aws --version
   ```

5. **Install kubectl:**
   ```bash
   curl -LO "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   chmod +x kubectl
   sudo mv kubectl /usr/local/bin/
   kubectl version --client
   ```

6. **Install eksctl:**
   ```bash
   curl -sLO "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_Linux_amd64.tar.gz"
   tar xz -f eksctl_Linux_amd64.tar.gz
   sudo mv eksctl /usr/local/bin/
   eksctl version
   ```

7. **Configure AWS CLI:**
   ```bash
   aws configure
   # Enter your Access Key ID, Secret Access Key, region (e.g., us-east-1), output format (json)
   ```

---

### Step 2 — Clone the Repository

```bash
git clone https://github.com/<YOUR_GITHUB_USERNAME>/bugboard.git
cd bugboard
```

---

### Step 3 — Build and Test Docker Image

```bash
# Build the Docker image
docker build -t bugboard:latest .

# Run the container locally to test
docker run -d -p 5000:5000 --name bugboard-test bugboard:latest

# Verify it works
curl http://localhost:5000/health
# Expected: {"app":"BugBoard","status":"healthy","version":"1.0.0"}

# Check the dashboard
curl http://localhost:5000/

# Stop and remove the test container
docker stop bugboard-test && docker rm bugboard-test
```

---

### Step 4 — Create Amazon ECR Repository and Push Image

```bash
# Create ECR repository
aws ecr create-repository --repository-name bugboard --region us-east-1

# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1

# Login to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Tag the image
docker tag bugboard:latest $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/bugboard:latest

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/bugboard:latest
```

---

### Step 5 — Create Amazon EKS Cluster

```bash
# Create the EKS cluster (this takes 15-20 minutes)
eksctl create cluster \
  --name bugboard-cluster \
  --region us-east-1 \
  --nodegroup-name bugboard-nodes \
  --node-type t3.small \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 3

# Verify the cluster
kubectl get nodes
```

---

### Step 6 — Deploy to EKS

Before deploying, update the image URI in `k8s/deployment.yaml`:

```bash
# Replace the placeholder with your actual ECR image URI
sed -i "s|image: .*|image: $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/bugboard:latest|" k8s/deployment.yaml

# Apply the Kubernetes manifests
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Check deployment status
kubectl get deployments
kubectl get pods
kubectl get services

# Get the external URL (LoadBalancer DNS)
kubectl get service bugboard-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

Visit the LoadBalancer URL in your browser to see BugBoard running on EKS!

---

### Step 7 — Set Up GitHub Actions CI/CD with OIDC

This uses OIDC (OpenID Connect) for secure AWS authentication — no long-lived access keys stored in GitHub.

#### 7a. Create an IAM OIDC Identity Provider

```bash
# Create the OIDC provider for GitHub Actions
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

#### 7b. Create an IAM Role for GitHub Actions

Create a file called `trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<AWS_ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:<YOUR_GITHUB_USERNAME>/bugboard:*"
        }
      }
    }
  ]
}
```

```bash
# Replace <AWS_ACCOUNT_ID> and <YOUR_GITHUB_USERNAME> in trust-policy.json first!

# Create the IAM role
aws iam create-role \
  --role-name GitHubActions-BugBoard-Role \
  --assume-role-policy-document file://trust-policy.json

# Attach policies for ECR and EKS access
aws iam attach-role-policy --role-name GitHubActions-BugBoard-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

aws iam attach-role-policy --role-name GitHubActions-BugBoard-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
```

#### 7c. Add the Role ARN to GitHub Secrets

1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Add a new secret: `AWS_ROLE_ARN` = `arn:aws:iam::<AWS_ACCOUNT_ID>:role/GitHubActions-BugBoard-Role`

Now every push to `main` will:
1. Run unit tests
2. Build the Docker image and push to ECR
3. Update `k8s/deployment.yaml` with the new image tag
4. Commit the manifest change — Argo CD picks it up automatically

---

### Step 8 — Install and Configure Argo CD

```bash
# Create the argocd namespace
kubectl create namespace argocd

# Install Argo CD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for Argo CD pods to be ready
kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=300s

# Expose Argo CD server (for demo — use LoadBalancer)
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'

# Get the Argo CD admin password
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
echo "Argo CD admin password: $ARGOCD_PASSWORD"

# Get the Argo CD URL
kubectl get svc argocd-server -n argocd -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

Log in to the Argo CD UI with username `admin` and the password above.

#### Apply the Argo CD Application

First, update `argocd/application.yaml` — replace `<YOUR_GITHUB_USERNAME>` with your actual username.

```bash
kubectl apply -f argocd/application.yaml
```

Argo CD will now:
- Monitor the `k8s/` folder in your GitHub repo
- Automatically sync any changes to the EKS cluster
- Self-heal if someone makes manual changes to the cluster

---

## Architecture Diagram

```
┌──────────┐     git push     ┌──────────────────┐
│Developer │ ───────────────► │   GitHub Repo     │
└──────────┘                  │   (bugboard)      │
                              └────────┬─────────┘
                                       │
                          ┌────────────▼────────────┐
                          │   GitHub Actions CI/CD   │
                          │  (OIDC Authentication)   │
                          ├──────────────────────────┤
                          │ 1. Run pytest tests      │
                          │ 2. Build Docker image    │
                          │ 3. Push to Amazon ECR    │
                          │ 4. Update k8s manifest   │
                          └────┬───────────┬────────┘
                               │           │
                  ┌────────────▼──┐   ┌────▼─────────────┐
                  │  Amazon ECR   │   │  Updated manifest │
                  │  (Container   │   │  committed to Git │
                  │   Registry)   │   └────┬─────────────┘
                  └────────┬──────┘        │
                           │    ┌──────────▼──────────┐
                           │    │     Argo CD          │
                           │    │  (GitOps Controller) │
                           │    │  auto-sync + heal    │
                           │    └──────────┬──────────┘
                           │               │
                  ┌────────▼───────────────▼──────────┐
                  │         Amazon EKS Cluster         │
                  │  ┌─────────────┐ ┌──────────────┐  │
                  │  │  Pod: Bug-  │ │  Pod: Bug-   │  │
                  │  │  Board (1)  │ │  Board (2)   │  │
                  │  └─────────────┘ └──────────────┘  │
                  │        ▲                 ▲         │
                  │        └──── Service ────┘         │
                  │           (LoadBalancer)            │
                  └────────────────┬───────────────────┘
                                   │
                          ┌────────▼────────┐
                          │    End Users     │
                          │  (Browser/HTTP)  │
                          └─────────────────┘
```

---

## Viva Preparation — Key Concepts

### Docker
- **What is Docker?** A platform to package applications into containers — lightweight, portable, isolated environments that include the app and all its dependencies.
- **What is a Dockerfile?** A text file with instructions to build a Docker image. Each instruction creates a layer.
- **What is the difference between an image and a container?** An image is a blueprint (read-only). A container is a running instance of an image.
- **Why do we use Gunicorn instead of Flask's built-in server?** Flask's dev server handles one request at a time. Gunicorn is a production WSGI server that spawns multiple worker processes.
- **What does `HEALTHCHECK` do in Docker?** It periodically runs a command to check if the container is healthy. Docker marks unhealthy containers for restart.

### Kubernetes (EKS)
- **What is Kubernetes?** An open-source container orchestration platform that automates deployment, scaling, and management of containerized applications.
- **What is Amazon EKS?** A managed Kubernetes service by AWS — AWS handles the control plane (API server, etcd, scheduler), and you manage the worker nodes.
- **What is a Deployment?** A Kubernetes object that manages a set of identical pods. It ensures the desired number of replicas are running and handles rolling updates.
- **What is a Service?** An abstraction that exposes pods to network traffic. A LoadBalancer Service gets an external URL from AWS.
- **What are liveness and readiness probes?** Liveness probes check if a container is alive (restart if not). Readiness probes check if it can receive traffic (remove from load balancer if not). Our app uses `/health` for both.
- **What does `replicas: 2` mean?** Kubernetes maintains 2 identical pods running our app for high availability.

### CI/CD (GitHub Actions)
- **What is CI/CD?** Continuous Integration (automatically test code on every push) and Continuous Deployment (automatically deploy tested code to production).
- **What is OIDC authentication?** OpenID Connect — GitHub Actions proves its identity to AWS using short-lived tokens instead of storing long-lived access keys. More secure because tokens expire automatically.
- **Why OIDC instead of access keys?** Access keys stored as GitHub Secrets can be leaked or compromised. OIDC tokens are generated per-run, last only minutes, and can be scoped to specific repos and branches.
- **What does our pipeline do?** (1) Run pytest, (2) Build Docker image, (3) Push to ECR, (4) Update the K8s manifest with the new image tag and commit it.

### GitOps (Argo CD)
- **What is GitOps?** A practice where Git is the single source of truth for infrastructure and application configuration. Changes are made through Git commits, not manual kubectl commands.
- **What is Argo CD?** A Kubernetes-native GitOps tool that watches a Git repository and automatically syncs the desired state (YAML manifests) to the cluster.
- **What does `selfHeal: true` do?** If someone manually changes something on the cluster (e.g., `kubectl edit`), Argo CD detects the drift and reverts it to match what's in Git.
- **What does `prune: true` do?** If you remove a resource from Git, Argo CD deletes it from the cluster too.
- **How does the full pipeline work?** Developer pushes code → GitHub Actions tests, builds, pushes image to ECR, updates manifest → Argo CD detects manifest change → Argo CD deploys new version to EKS → Users see the update.

### Amazon ECR
- **What is ECR?** Amazon Elastic Container Registry — a fully managed Docker image registry. Like Docker Hub but private and integrated with AWS.
- **Why use ECR over Docker Hub?** ECR is private by default, integrates with IAM for access control, and is in the same AWS network as EKS (faster image pulls).

---

*Built with care for CSA3004 Cloud Native Orchestration — BCA Sem V, DYPIU Pune*
