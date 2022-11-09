FROM python:3.8

RUN pip install --upgrade pip

VOLUME /opt/app/epub
VOLUME /opt/app/out
WORKDIR /opt/app

ENV PATH="/home/app/.local/bin:${PATH}"

COPY requirements.txt .
COPY env.yml .

RUN pip install -r requirements.txt && \
	rm requirements.txt

COPY . .

 ENTRYPOINT ["python", "main.py"]