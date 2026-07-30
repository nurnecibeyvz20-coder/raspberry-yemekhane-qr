FROM python:3.12-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /opt/piper && \
    python -m piper.download_voices --download-dir /opt/piper tr_TR-dfki-medium 2>/dev/null || \
    (apt-get update && apt-get install -y --no-install-recommends curl && \
     curl -fsSL -o /opt/piper/tr_TR-dfki-medium.onnx \
       "https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium/tr_TR-dfki-medium.onnx" && \
     curl -fsSL -o /opt/piper/tr_TR-dfki-medium.onnx.json \
       "https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium/tr_TR-dfki-medium.onnx.json" && \
     apt-get purge -y curl && rm -rf /var/lib/apt/lists/*)
ENV PIPER_MODEL=/opt/piper/tr_TR-dfki-medium.onnx
COPY . /code/app
ENV PYTHONPATH=/code
RUN chmod +x /code/app/entrypoint.sh
ENTRYPOINT ["/code/app/entrypoint.sh"]
