FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# Install CPU-only torch first (much smaller than default GPU torch)
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining requirements
RUN pip install -r requirements.txt

# Pre-download the cross-encoder reranker model so it's baked into the image
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# GCS client for downloading chroma databases at startup
RUN pip install --no-cache-dir google-cloud-storage

EXPOSE 8080

COPY . .

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]