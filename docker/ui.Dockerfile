# ui/Dockerfile
FROM python:3.11-slim

WORKDIR /code

COPY requirements-ui.txt .
RUN pip install --no-cache-dir -r requirements-ui.txt --break-system-packages

COPY ui.py .

EXPOSE 8501

CMD ["streamlit", "run", "ui.py", "--server.address=0.0.0.0", "--server.port=8501"]
