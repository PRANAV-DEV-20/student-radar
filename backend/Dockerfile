FROM python:3.11-slim

WORKDIR /app

# Every dependency ships a CPython 3.11 Linux wheel (psycopg2-binary, Pillow,
# PyMuPDF, cryptography, ...), so no compiler toolchain or Debian mirror is
# needed. Health checks use Python's urllib, not curl.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/start.sh

EXPOSE 8000

CMD ["sh", "/app/start.sh"]

