# 🧠 AWS RAG Application Template for GoMiLERS

This repository provides a modular and extensible template for building **Retrieval-Augmented Generation (RAG)** applications on AWS. The architecture leverages core AWS services such as **Amazon Bedrock**, **OpenSearch**, **Polly**, **S3**, and **DynamoDB**, combined with a Python-based backend. The template is designed for fast prototyping, scalability, and production-readiness with minimal modifications.

---

## 📁 Project Structure

```
.
│   .dockerignore
│   .env
│   .env.example
│   .gitignore
│   .pre-commit-config.yaml
│   Dockerfile
│   Dockerfile-local
│   Makefile
│   README.md
│   requirements.txt
│
├───.github/
│   └───workflows/
│           deployment.yml
│
├───scripts/
│       build.sh
│
├───src/
│   │   constants.py
│   │   generate.py
│   │   main.py
│   │   test.py
│   │   __init__.py
│   │
│   ├───config/
│   │       model_config.yaml
│   │       prompt_config.yaml
│   │       queries_config.yaml
│   │
│   ├───handlers/
│   │       bedrock.py
│   │       dynamo_db.py
│   │       nova_sonic.py
│   │       opensearch.py
│   │       polly.py
│   │       s3.py
│   │       secret_manager.py
│   │       transcribe.py
│   │
│   ├───services/
│   │       schema.py
│   │
│   └───utils/
│           utils.py
│
└───tests/
    └───handlers/
            test_bedrock.py
            test_database.py
            test_opensearch.py
            test_s3.py
```

---

## 🛠 Setup Instructions

1. **Clone the Repository**

   ```bash
   git clone <REPO_URL>
   cd <cloned_folder>
   ```

2. **Open in IDE**
   Open the folder in **VSCode** or **PyCharm**.

3. **Create a Conda Environment (Recommended)**

   ```bash
   conda create -n rag_app python=3.12
   conda activate rag_app
   ```

   👉 [Install Anaconda](https://www.anaconda.com/download)

4. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   > **Note**: We use [Poetry](https://python-poetry.org/) to manage dependencies and generate `requirements.txt`.
   > [About Poetry](https://medium.com/@atharvapatilap27/simplifying-python-dependency-management-with-poetry-0ab480a699b6)

---

## 🤩 Code Structure and Logic

### 🔹 Root Files

| File                             | Description                                                                  |
| -------------------------------- | ---------------------------------------------------------------------------- |
| `.env` / `.env.example`          | Environment variables used for local and production environments.            |
| `Dockerfile`, `Dockerfile-local` | Build instructions for containerizing the app (prod and local respectively). |
| `Makefile`                       | CLI automation tool for common tasks (e.g., build, run, test).               |
| `.pre-commit-config.yaml`        | Pre-commit hooks configuration for linting and code formatting.              |
| `requirements.txt`               | Python dependencies exported from Poetry.                                    |
| `README.md`                      | Project documentation.                                                       |

---

### 🔹 `src/` — Main Application Code

#### ✅ Root-level Python Files

| File           | Purpose                                                |
| -------------- | ------------------------------------------------------ |
| `main.py`      | Entry point of the application; starts the app server. |
| `generate.py`  | Core file where API endpoints are to be written.       |
| `test.py`      | Sanity test script for basic component validation.     |
| `constants.py` | Application-wide constants and configurations.         |
| `__init__.py`  | Makes `src` a Python package.                          |

#### 📜 `config/` — YAML Configuration Files

| File                  | Description                                                          |
| --------------------- | -------------------------------------------------------------------- |
| `model_config.yaml`   | Model-specific parameters (e.g., LLM type, temperature, max tokens). |
| `prompt_config.yaml`  | Prompt templates used in RAG generation.                             |
| `queries_config.yaml` | Search/query templates used to retrieve context.                     |

#### 🔧 `handlers/` — Integration Modules

| File                | Purpose                                                                                     |
| ------------------- | ------------------------------------------------------------------------------------------- |
| `bedrock.py`        | Interface for interacting with Amazon Bedrock (LLMs like Anthropic Claude, Jurassic, etc.). |
| `dynamo_db.py`      | Functions to read/write metadata or session history from/to DynamoDB.                       |
| `nova_sonic.py`     | Custom audio processing or ML logic module (placeholder; extend as needed).                 |
| `opensearch.py`     | Interfaces with OpenSearch for vector or text-based document retrieval.                     |
| `polly.py`          | Text-to-speech functionality using Amazon Polly.                                            |
| `s3.py`             | Upload/download files to/from S3 buckets.                                                   |
| `secret_manager.py` | Fetch credentials/secrets securely using AWS Secrets Manager.                               |
| `transcribe.py`     | Uses AWS Transcribe for converting speech/audio to text.                                    |

#### 🤬 `services/` — Data Models / Schemas

| File        | Description                                                         |
| ----------- | ------------------------------------------------------------------- |
| `schema.py` | Pydantic models for input/output validation and API data contracts. |

#### 🧰 `utils/` — Utility Functions

| File       | Purpose                                                      |
| ---------- | ------------------------------------------------------------ |
| `utils.py` | Common helper functions for logging, file ops, parsing, etc. |

---

### 🔍 `tests/` — Unit Tests

| File                 | Tests                             |
| -------------------- | --------------------------------- |
| `test_bedrock.py`    | LLM generation logic via Bedrock. |
| `test_database.py`   | CRUD operations on DynamoDB.      |
| `test_opensearch.py` | Document indexing and retrieval.  |
| `test_s3.py`         | File operations with AWS S3.      |

> 🧪 Testing is done using `pytest`. More unit and integration tests can be added to improve coverage.

---

## 🚀 Features

- 📆 Modular architecture — plug-and-play AWS service integrations.
- 🤖 Bedrock-compatible — easily connect to Claude, Titan, or Jurassic.
- 🔍 RAG pipeline ready — integrate vector search with OpenSearch.
- 🧠 Prompt-configurable — YAML-based dynamic prompt handling.
- 🎤 Speech support — transcription and TTS via AWS services.
- 🧪 Test suite scaffolded for rapid development and CI/CD integration.
- 🐳 Docker-ready — deploy locally or in containerized environments.
- ⚙️ Poetry-based dependency management for clean, reproducible builds.

---

## 📌 Future Enhancements

- ✅ Web frontend integration (e.g., Streamlit or React).
- ✅ Support for LangChain or LlamaIndex frameworks.
- 🔐 Cognito-based user authentication.
- 🔊 Multimodal RAG: audio/image/text input support.
- 📊 Usage analytics and logging dashboard (via CloudWatch or ELK stack).

---

## 👨‍💼 Contributing

We welcome contributions! Please open an issue or submit a PR for improvements, bug fixes, or feature requests.

---

## 📄 License

This project is licensed under the MIT License. See `LICENSE` for more information.
