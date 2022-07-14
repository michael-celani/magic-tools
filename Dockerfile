# syntax=docker/dockerfile:1
FROM python:3.11.0b3-bullseye
WORKDIR /app

RUN pip3 install python-dateutil requests moxfield==0.4.2 discord.py python-dotenv 
COPY ./src /app/src
WORKDIR /app/src
CMD [ "python3", "./bot.py" ]