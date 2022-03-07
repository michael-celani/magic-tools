# syntax=docker/dockerfile:1
FROM python:3.10.2-bullseye
WORKDIR /app

RUN pip3 install python-dateutil requests moxfield discord.py python-dotenv 
COPY . .
WORKDIR /app/src
CMD [ "python3", "./bot.py" ]