FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Non-root user
RUN useradd --create-home appuser
USER appuser

# Default: run scheduler
CMD ["python", "-m", "src.main"]
