FROM python:3.14

WORKDIR /server

COPY ./requirements.txt /server/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /server/requirements.txt

COPY ./server /server

RUN apt update \
    && apt install -y ffmpeg \
    && rm -rf /var/lib/apt/lists/*

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]