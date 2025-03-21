FROM python:3.8

WORKDIR /app
COPY . /app

RUN pip install spade
RUN chmod +x main.py

CMD python -u main.py
