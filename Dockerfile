FROM koodivaramu.eesti.ee:5050/taltechnlp/kiirkirjutaja:0.2.7

COPY requirements.txt .

RUN pip install --user -r requirements.txt && \
    rm requirements.txt

ENV PYTHONPATH="${PYTHONPATH}:/opt/kiirkirjutaja"

VOLUME /opt/app/audio
WORKDIR /opt/app

COPY . .

RUN ln -s /opt/kiirkirjutaja && ln -s /opt/models

ENTRYPOINT ["python", "main.py"]