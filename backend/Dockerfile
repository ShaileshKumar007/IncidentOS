# IncidentOS Backend Dockerfile (Milestone 3A)
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (Git required for git tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend application
COPY backend/app /app/app
COPY demo-environment /app/demo-environment

# Default environment variables
ENV BACKEND_HOST="0.0.0.0"
ENV BACKEND_PORT="8000"
ENV DEMO_WORKSPACE_ROOT="/app/demo-environment"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
