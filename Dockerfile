FROM python:3.6
ENV PYTHONUNBUFFERED
RUN mkdir /code
WORKDIR /code
ADD . /code/
RUN pip install -r requirements.txt


