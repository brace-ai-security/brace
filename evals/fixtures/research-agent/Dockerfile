FROM python:3.12-slim@sha256:2be8daddbb82756f7d1f2c7ece706aadcb284bf6ab6d769ea695cc3ed6016743

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY prompts/ prompts/
COPY config/ config/

RUN useradd --uid 10001 --no-create-home app
USER 10001
EXPOSE 8000
CMD ["uvicorn", "src.web:app", "--host", "0.0.0.0", "--port", "8000"]
