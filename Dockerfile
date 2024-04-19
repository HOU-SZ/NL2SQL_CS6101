FROM ubuntu:22.04
ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"
RUN apt-get update

RUN apt-get install -y wget && rm -rf /var/lib/apt/lists/*

RUN wget \
    https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && mkdir /root/.conda \
    && bash Miniconda3-latest-Linux-x86_64.sh -b \
    && rm -f Miniconda3-latest-Linux-x86_64.sh 
RUN conda --version

RUN git clone https://github.com/HOU-SZ/NL2SQL_CS6101.git
RUN cd NL2SQL_CS6101
RUN conda create -n nl2sql_cs6101 python=3.10
RUN conda activate nl2sql_cs6101
RUN pip install -r requirements.txt

RUN pip install -U "huggingface_hub[cli]"
RUN huggingface-cli download defog/sqlcoder-7b-2 --local-dir sqlcoder-7b-2
RUN cd app

CMD ["python", "app.py"]

