FROM python:3.8-slim

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

EXPOSE 5000

ENV NAME World

ENTRYPOINT ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--timeout", "0", "--workers", "4"]