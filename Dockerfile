FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml requirements-dev.lock ./
COPY backend ./backend
COPY scripts ./scripts
RUN pip install --no-cache-dir -c requirements-dev.lock '.[platform]' \
    && useradd --create-home --uid 10001 substrata \
    && mkdir -p /app/data/models \
    && chown -R substrata:substrata /app/data

USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "substrata.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
