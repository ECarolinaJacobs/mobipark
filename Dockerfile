FROM python:3.11-slim

WORKDIR /workspace

# Install system dependencies for building pysqlcipher3
RUN apt-get update && \
    apt-get install -y gcc libsqlcipher-dev curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install uv 
RUN uv pip install --system "fastapi[standard]" -r requirements.txt

COPY . .

EXPOSE 8000

COPY <<EOF /start.sh
#!/bin/bash
set -e
# Start uvicorn in background
uvicorn main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=\$!
# Wait for server to be ready
echo "Waiting for server to start..."
for i in {1..30}; do
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "Server is ready!"
    break
  fi
  sleep 1
done
# Run tests
pytest
# Keep uvicorn running
wait \$UVICORN_PID
EOF

RUN chmod +x /start.sh

CMD ["/start.sh"]
