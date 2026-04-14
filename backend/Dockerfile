FROM python:3.12.11-slim

WORKDIR /app

# Create non-root user before installing deps
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hand ownership to the non-root user
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
