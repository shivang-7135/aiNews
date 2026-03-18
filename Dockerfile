FROM python:3.11-slim

WORKDIR /app

# Ensure Python output is sent straight to terminal (for Render logs)
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render injects PORT env var; default to 8000 for local use
ENV PORT=8000
EXPOSE $PORT

CMD uvicorn app:app --host 0.0.0.0 --port $PORT
