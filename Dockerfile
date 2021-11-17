FROM koodivaramu.eesti.ee:5050/taltechnlp/kiirkirjutaja:0.2.1

COPY requirements.txt .

RUN pip install --user -r requirements.txt && \
    rm requirements.txt

COPY . .

RUN echo "python asr_main.py" > entrypoint.sh

ENTRYPOINT ["bash", "entrypoint.sh"]