# syntax=docker/dockerfile:1

#FROM python:3.8-slim-buster
FROM python:3.7
WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt -i https://pypi.douban.com/simple

COPY . .

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]