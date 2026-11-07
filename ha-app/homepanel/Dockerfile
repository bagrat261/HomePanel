FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY source/ ./
RUN pip install --no-cache-dir . && useradd --uid 10001 --create-home panel
COPY run.py /app/run.py
USER panel
EXPOSE 8090
CMD ["python", "/app/run.py"]
