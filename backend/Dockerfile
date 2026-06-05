FROM python:3.12

WORKDIR /app

RUN pip install gunicorn==25.3.0 --index-url https://pypi.python.org/simple

COPY requirements.txt .

RUN pip install -r requirements.txt --index-url https://pypi.python.org/simple --no-cache-dir

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "foodgram_backend.wsgi"]