FROM ubuntu:22.04
ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"
RUN apt-get update

RUN apt-get install -y wget && rm -rf /var/lib/apt/lists/*

RUN wget \
    https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && mkdir /root/.conda \
    && bash Miniconda3-latest-Linux-x86_64.sh -b \
    && rm -f Miniconda3-latest-Linux-x86_64.sh \
    && echo "Running $(conda --version)" \
    && conda init bash \
    && . /root/.bashrc \
    && conda update conda \
    && conda create -n nl2sql_cs6101 python=3.10 -y \
    && conda activate nl2sql_cs6101

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN pwd
WORKDIR /app/app

CMD ["python", "app.py"]

