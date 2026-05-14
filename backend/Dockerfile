FROM python:3.12-slim

WORKDIR /app

# Keep the venv outside /app so bind mounts don't wipe it on container start.
ENV UV_PROJECT_ENVIRONMENT=/opt/.venv
ENV PATH="/opt/.venv/bin:$PATH"

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
