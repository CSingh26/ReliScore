FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY services/model/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/model/app ./app
COPY services/model/artifacts ./artifacts

ENV MODEL_ARTIFACTS_ROOT=/app/artifacts
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
