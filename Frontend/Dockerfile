FROM python:3.12-alpine
WORKDIR /app
ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 5000
CMD [ "python", "serving.py" ]