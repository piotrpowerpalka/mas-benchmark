FROM python:3.8

WORKDIR /app
COPY . /app

RUN pip install spade
RUN chmod +x main.py
# Use environment variables passed from docker-compose

CMD python -u main.py 
