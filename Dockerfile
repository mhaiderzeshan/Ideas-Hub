FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your FastAPI project
COPY . .

# Copy Aiven CA certificate for secure MySQL connection
COPY ca.pem /etc/ssl/certs/ca.pem

# (Optional) Document the internal port (Render ignores this)
EXPOSE 8000

# ✅ Use Render's assigned port (e.g., 10000) dynamically
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
