FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Render runs this CMD directly for Docker-type services and does NOT read
# the Procfile's `release:` line — that only applies to Heroku-style
# buildpack deploys. Migrations have to happen here instead, or they never
# run at all. --proxy-headers: trust X-Forwarded-* from the platform's load
# balancer/proxy so request.client and redirects behave correctly behind TLS.
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
