
# Self-Hosting LLMs (Ollama + FastAPI + HTML Frontend)

Minimal stack for running Large Language Models locally (or in AWS) using:

- **[Ollama](https://ollama.com/)** as the model runtime
- **FastAPI** backend for chat, model management, and streaming
- **Vanilla HTML/JS** frontend
- **Docker Compose** for local development
- **CloudFormation** template for AWS ECS (Fargate) + EC2

---

# [Demo Video](https://vimeo.com/1116522339) on [Vimeo](https://vimeo.com/)

---

## 📂 Repository Structure

```bash
.
├── backend/                # FastAPI service
│   └── app.py             
│   └── requirements.txt
│   └── Dockerfile             
├── frontend/               # static HTML/JS chat UI
│   └── index.html          
├── docker-compose.yml      # Local stack (Ollama + Backend)
├── cfn_template.yaml       # CloudFormation template
└── README.md
```


---

## 🚀 Features

- **Chat streaming** via Server-Sent Events
- **Session persistence** (per `session_id`)
- **Model management**:
  - list available models
  - pull new models from Ollama registry
  - delete unused models
- **Frontend UI** with:
  - markdown rendering
  - model dropdown
  - model confirmation for deletes

---

## 🧑‍💻 Local Development (Docker Compose)

### 1. Prerequisites
- Docker & Docker Compose
- Ports **11434** (Ollama) and **9000** (FastAPI) open

### 2. Run
```bash
git clone https://github.com/nagi1995/self-hosting-LLMs.git
cd self-hosting-LLMs
docker compose up --build
````

This starts:

* **Ollama** on `http://localhost:11434`
* **FastAPI Backend** on `http://localhost:9000`
* **Frontend** is just the `frontend/index.html` file — open it directly in a browser.

### 3. Environment Variables

Backend uses:

* `OLLAMA_URL` (default `http://localhost:11434`)

---

## 🧩 Backend API

| Endpoint           | Method | Description                                                       |
| ------------------ | ------ | ----------------------------------------------------------------- |
| `/health`          | GET    | Health check (Ollama reachability)                                |
| `/chat`            | GET    | Stream chat completion (`prompt`, `session_id`, `model` required) |
| `/models/list`     | GET    | List locally available models                                     |
| `/models/download` | POST   | Pull a new model (`{"model":"llama3"}`)                           |
| `/models/delete`   | POST   | Delete one or more models (`{"models":["llama3"]}`)               |

---

## 🌐 AWS Deployment (CloudFormation)

## 📊 AWS Architecture

![AWS Architecture](demo/draw.svg)


`cfn_tenplate.yaml` provisions:

* **ECS Fargate** service for FastAPI backend
* **ECS EC2 (host)** service for Ollama
* Security groups restricting port 9000 to your IP
* IAM roles, CloudWatch logs, and persistent EBS volume for models

### 1. Prerequisites

* AWS CLI configured
* An **ECR repository** with your **backend image** pushed (`latest` tag)
* Existing **VPC** and **subnets**

### 2. Deploy

```bash
aws cloudformation deploy \
  --template-file cfn_template.yaml \
  --stack-name ollama-stack \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    MyIp=<your-ip-address>/32 \
    VpcId=<vpc-id> \
    SubnetIds='<subnet-ids>' \
    EcrRepoName=be-image
```

### 3. Outputs

* **BackendServiceName** – Fargate ECS Service
* **OllamaInstanceId** – EC2 instance running Ollama
* **BackendSecurityGroup** – restricts port 9000 to your IP

---

## 🖥️ Frontend Usage

1. Edit `frontend/index.html` → set:

   ```js
   const API_BASE = "http://<backend-host>:9000";
   ```
2. Open the HTML file in a browser.
3. Choose a model, type a prompt, hit **Send**. Streaming markdown output will render live.

---

## 🔐 Notes

* CORS is open (`*`) for simplicity — **tighten it in production**.
* Ollama volumes are persisted (`ollama_models`) for local Docker and `/var/lib/ollama` for AWS EC2.
* Adjust EC2 instance size / EBS volume in `cfn_template.yaml` to fit your model sizes.

---


