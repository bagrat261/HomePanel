FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY homepanel ./homepanel
COPY configuration ./configuration
RUN pip install --no-cache-dir . && useradd --uid 10001 --create-home panel
USER panel
EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/health', timeout=3)"
CMD ["uvicorn", "homepanel.app:app", "--host", "0.0.0.0", "--port", "8090", "--no-proxy-headers"]
