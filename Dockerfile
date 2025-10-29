# Use the UV base image (includes Python + UV preinstalled)
FROM ghcr.io/astral-sh/uv:debian

# Set working directory
WORKDIR /app

# ----------------------------
# 1️⃣ Install system dependencies first (cached layer)
# ----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------
# 2️⃣ Copy dependency definitions only (for build cache efficiency)
# ----------------------------
COPY pyproject.toml /app/
# If you use UV lockfile for reproducibility, copy it too:
# COPY uv.lock /app/

# ----------------------------
# 3️⃣ Install Python dependencies with UV
# ----------------------------
RUN uv sync

# ----------------------------
# 4️⃣ Copy the full application code
# ----------------------------
COPY . /app/

# ----------------------------
# 5️⃣ Environment configuration
# ----------------------------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Expose Chainlit port
EXPOSE 8000

# ----------------------------
# 6️⃣ Run the Chainlit app
# ----------------------------
CMD ["bash", "-c", "source .venv/bin/activate && chainlit run main.py --host 0.0.0.0 --port 8000"]
