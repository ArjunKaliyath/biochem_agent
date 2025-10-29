# 🧬 Biochem-Agent: Agentic Biochemical Data Analysis Assistant

An interactive AI assistant for **biochemical and pathway enrichment analysis**, built with **Chainlit**, **OpenAI**, and **Tavily**.

It combines a conversational UI with sandboxed code execution — allowing scientists and developers to analyze datasets, generate visualizations, and search biochemical literature seamlessly.

---

## 🚀 Quick Start

### 🐳 Using Docker (Recommended)

Docker provides a prebuilt, isolated environment that already includes Python, UV, and all required dependencies.

```bash
# Clone the repository
git clone https://github.com/<yourusername>/biochem-agent.git
cd biochem-agent

# Build the Docker image
docker build -t biochem-agent .

# Run the container
docker run -p 8000:8000 -it biochem-agent
````

Then open your browser at **[http://localhost:8000](http://localhost:8000)**.


---

### 💻 Local Installation (Developer Mode)

If you want to develop or customize the app locally, install [**UV**](https://docs.astral.sh/uv/) first.

#### 1️⃣ Setup

```bash
# Install uv (only once)
pip install uv

# Clone the repository
git clone https://github.com/<yourusername>/biochem-agent.git
cd biochem-agent

# Sync environment and dependencies
uv sync
**For macOS/Linux:**
source .venv/bin/activate

**For Windows**
.venv\Scripts\activate

**or run**
uv run chainlit run main.py
```

#### 2️⃣ Run the Chainlit App

```bash
chainlit run main.py
```

Then visit [http://localhost:8000](http://localhost:8000).

---

## 🔑 Environment Variables

Before running, create a `.env` file in the project root with your API keys:


For local run - 

> These are automatically loaded at runtime by **python-dotenv**.

For Docker - 

```bash
docker run --env-file .env -p 8000:8000 biochem-agent
```

---

## 🧩 Project Structure

```
biochem-agent/
│
├── main.py                     # Chainlit app entrypoint
├── db.py                       # Session data manager
├── tools/
│   ├── __init__.py
│   ├── local_code_runner.py    # Secure sandboxed Python code runner
│   ├── types.py                # ToolResult definitions
│
├── tools.json                  # Tool schemas (tavily_search, local_code_run)
├── pyproject.toml              # Dependency definitions for UV
├── Dockerfile                  # Container configuration
├── .dockerignore               # Ignored files for Docker build
└── README.md
```

---

## 🐍 Technology Stack

| Layer            | Tools                                                         |
| ---------------- | ------------------------------------------------------------- |
| Frontend         | **Chainlit**                                                  |
| Backend          | **Python 3.11+**, **async/await architecture**                |
| AI APIs          | **OpenAI Responses API**, **Tavily Search**                   |
| Data Libraries   | `pandas`, `numpy`, `matplotlib`, `seaborn`, `plotly`, `scipy` |
| Environment      | **python-dotenv**, **UV**                                     |
| Containerization | **Docker** (with `ghcr.io/astral-sh/uv` base image)           |


## 🧠 Features

* **Natural language dataset analysis** via OpenAI Responses API
* **Sandboxed local code execution** using a subprocess-safe runner
* **Automatic CSV summarization** (schema, stats, distributions)
* **Interactive biochemical visualizations** (bar plots, dot plots, pathway maps)
* **Web literature search** through Tavily
* **Session-based storage** and cleanup between users
* **Automatic retry mechanism** for self-correcting code generations

---

## 🔒 Security & Isolation

The **local code runner** executes user-generated Python code inside a **restricted subprocess** that:

* Runs in a temporary directory under `/app/runs/<session_id>`
* Has **no network access**
* Can only import whitelisted libraries (`pandas`, `numpy`, `matplotlib`, `seaborn`, `plotly`, `scipy`, etc.)
* Automatically cleans up on chat end or container stop


---

## 🧾 License

MIT License © 2025 Arjun Kaliyath

---

