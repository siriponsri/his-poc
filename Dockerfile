FROM node:24.22.1-bookworm-slim@sha256:be8204d4bd327363357f532187b752ff62759c31bedf98e9e18fc08c9cbd605c AS web
RUN apt-get update && apt-get install -y --no-install-recommends python3 python-is-python3 \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app/apps/web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web ./
COPY backend/app/domains/clinical_catalog.json backend/app/domains/erp_catalog.json /app/backend/app/domains/
RUN npm run build

FROM python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
# PG client tools are required for real D38 backup/isolated-restore jobs.
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
 && install -d /usr/share/postgresql-common/pgdg \
 && curl --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
 && echo 'deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main' > /etc/apt/sources.list.d/pgdg.list \
 && apt-get update && apt-get install -y --no-install-recommends postgresql-client-18=18.6-1.pgdg12+2 \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-backend.txt ./
RUN pip install --no-cache-dir -r requirements-backend.txt
COPY . .
COPY --from=web /app/apps/web/dist /app/apps/web/dist
RUN useradd --uid 10001 --create-home his && mkdir -p /var/his/files /var/his/backups && chown -R his:his /var/his
USER his
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
