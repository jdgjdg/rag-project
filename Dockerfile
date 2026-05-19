FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# Install CPU-only torch first (much smaller than default GPU torch)
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining requirements
RUN pip install -r requirements.txt

EXPOSE 8080

COPY . .

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]