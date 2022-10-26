FROM continuumio/miniconda3

VOLUME /opt/app/epub
VOLUME /opt/app/out
WORKDIR /opt/app

COPY requirements.txt .
COPY env.yml .
RUN conda env create -f env.yml

RUN echo "conda activate myenv" >> ~/.bashrc
ENV PATH="/opt/conda/envs/myenv/bin:${PATH}"

# SHELL ["/bin/bash", "--login", "-c"]
# SHELL ["conda", "run", "-n", "myenv", "/bin/bash", "-c"]

RUN pip install --upgrade pip
RUN pip install --user -r requirements.txt && \
	rm requirements.txt
RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get install -y ffmpeg
#RUN git clone https://github.com/TartuNLP/tts_preprocess_et /opt/app/tts_preprocess_et
# /root/.local/bin:

COPY . .

ENTRYPOINT ["./entrypoint.sh"]
# ENTRYPOINT ["python", "main.py"]
# ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "myenv", "python", "main.py"]