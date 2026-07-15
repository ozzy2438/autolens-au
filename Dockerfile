FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
RUN python -m pip install --no-cache-dir uv==0.6.13 \
    && uv sync --frozen --no-dev --no-install-project

RUN addgroup --system autolens && adduser --system --ingroup autolens autolens
COPY --chown=autolens:autolens . .
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:${PATH}"
USER autolens

EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
