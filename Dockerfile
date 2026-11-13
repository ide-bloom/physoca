FROM python:3.12-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 shared-mime-info \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 physoca

COPY --from=builder /install /usr/local
USER physoca
EXPOSE 8000
CMD ["physoca", "serve", "--host", "0.0.0.0", "--port", "8000"]
