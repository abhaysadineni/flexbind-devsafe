FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/jobs

EXPOSE 8000

CMD sh -c "celery -A app.worker worker --loglevel=info --concurrency=1 & uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
```

**5.** Click **Commit changes** → **Commit changes**

---

Now wait 5–10 minutes for Render to rebuild the backend. Then:

**Check if the backend is actually alive:**

Open this in your browser (replace with your actual backend URL):
```
https://flexbind-api-xxxx.onrender.com/health
