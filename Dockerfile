FROM alumae/kaldi-offline-transcriber-et:latest

COPY requirements.txt .

RUN pip install --user -r requirements.txt && \
    rm requirements.txt

COPY . .

RUN echo "python main.py" > entrypoint.sh

ENTRYPOINT ["bash", "entrypoint.sh"]