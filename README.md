# 🚀 DockMate  
### *Automated Dockerfile Generation • CI/CD Testing • Repo Analysis • AWS Deployment*

DockMate is a **DevOps automation tool** that analyzes GitHub repositories, generates optimized Dockerfiles and CI/CD workflows, performs automated API testing, and even deploys containerized applications to AWS.

This project includes a **FastAPI backend**, **React frontend**, **Postman/Newman test suite**, and **full CI/CD pipelines** using **GitHub Actions** and **Jenkins**.

---

## 📑 Table of Contents

- [Features](#-features)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Backend Setup](#-backend-setup)
- [Frontend Setup](#-frontend-setup)
- [Running with Docker Compose](#-running-with-docker-compose)
- [Running Tests (Newman)](#-running-tests-newman)
- [CI/CD (GitHub Actions)](#-cicd-github-actions)
- [CI/CD (Jenkins)](#-cicd-jenkins)
- [Environment Variables](#-environment-variables)
- [Screenshots](#-screenshots)
- [License](#-license)

---

## ✨ Features

✔ Submit a GitHub repo and auto-generate:
- Dockerfile  
- docker-compose.yml  
- CI/CD workflow  
- Optimization report  

✔ Sparse clone + static analysis  
✔ JWT Authentication  
✔ Repository history tracking  
✔ AWS deployment (ECR + ECS)  
✔ Postman tests + Newman automation  
✔ Clean UI built with React + Tailwind  
✔ CORS-enabled backend for local dev  
✔ Fully containerized

---

## 📂 Project Structure

```
dockmate/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── utils/
│   │   └── main.py
│   ├── venv/
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── .env.example
│   ├── vite.config.js
│   └── package.json
│
├── tests/
│   └── postman/
│       ├── DockMate.postman_collection.json
│       ├── DockMate.postman_environment.json
│       └── newman.html (output)
│
├── docker-compose.yml
├── Jenkinsfile
└── .github/workflows/api-ci.yml
```

---

## 🛠 Prerequisites

Install these before running the project:

### 🔹 Backend requirements
- Python 3.10+
- pip
- virtualenv

### 🔹 Frontend requirements
- Node.js 18+
- npm / yarn / pnpm

### 🔹 Testing requirements
```
npm install -g newman newman-reporter-htmlextra
```

### 🔹 Optional (for full CI/CD)
- Docker
- Jenkins
- GitHub Actions enabled
- AWS credentials (for deploy)

---

## 🧩 Backend Setup

```
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Backend runs at:

👉 **http://localhost:8000**

Health check:

👉 **http://localhost:8000/health**

---

## 🎨 Frontend Setup

```
cd frontend
cp .env.example .env
npm install
npm run dev
```

Frontend runs at:

👉 **http://localhost:5173**

---

## 🐳 Running with Docker Compose

```
docker-compose up --build
```

Backend → http://localhost:8000  
Frontend → http://localhost:5173  

---

## 🧪 Running Tests (Newman)

```
newman run tests/postman/DockMate.postman_collection.json \
    -e tests/postman/DockMate.postman_environment.json \
    --reporters cli,htmlextra \
    --reporter-htmlextra-export newman.html
```

Outputs:
- CLI results
- `newman.html` report file

---

## ⚙️ CI/CD (GitHub Actions)

📍 Workflow location:

```
.github/workflows/api-ci.yml
```

Pipeline does:

1. Install Python  
2. Run FastAPI  
3. Install Node.js  
4. Install Newman  
5. Run entire Postman suite  
6. Upload artifact report

---

## 🏗 CI/CD (Jenkins)

Your Jenkinsfile performs:

- Backend install  
- Newman tests  
- HTML test report publishing  
- Optional AWS deployment 

To run locally:

```
docker run -p 8080:8080 jenkins/jenkins:lts
```

---

## 🔐 Environment Variables

### Backend `.env`
```
JWT_SECRET=your_secret
SUPABASE_URL=optional
SUPABASE_KEY=optional

AWS_ACCESS_KEY_ID=optional
AWS_SECRET_ACCESS_KEY=optional
AWS_DEFAULT_REGION=us-east-1
```

### Frontend `.env`
```
VITE_API_URL=http://localhost:8000
```

---

## 🖼 Screenshots (Optional)

_Add UI screenshots here_

---

## 📜 License

MIT © 2025 DockMate
