FROM python:3.11-slim
WORKDIR /artifact
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["bash", "scripts/run_all_local.sh"]
