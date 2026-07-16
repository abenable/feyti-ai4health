# Use a lightweight Python base image
FROM python:3.10-slim-bookworm

# Prevent Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# Prevent Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Install system dependencies required for uv and potentially python-docx
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer and resolver)
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/usr/local/bin" sh

# Copy the dependency lockfile and project file
COPY pyproject.toml uv.lock ./

# Install dependencies using uv into the system python environment
RUN uv sync --frozen --no-dev --no-install-project

# Copy the rest of the application code
COPY . .

# Create a non-root user to run the application for security
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# Expose the FastAPI default port
EXPOSE 8000

# Start the FastAPI application with Uvicorn worker
CMD ["uv", "run", "fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]