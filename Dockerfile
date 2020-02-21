FROM python:3.7-slim-stretch
ADD . /code
WORKDIR /code
RUN pip install -r requirements.txt
EXPOSE 8000
RUN ["python", "app.py"]
