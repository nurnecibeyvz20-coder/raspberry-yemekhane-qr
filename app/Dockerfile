FROM python:3.12-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /code/app
ENV PYTHONPATH=/code
RUN chmod +x /code/app/entrypoint.sh
ENTRYPOINT ["/code/app/entrypoint.sh"]
