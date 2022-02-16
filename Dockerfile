FROM python:3.9-slim

RUN \
    # Print executed commands to terminal.
    set -ex ; \
    savedAptMark="$(apt-mark showmanual)" ; \
    apt-get update ; \
    apt install -y build-essential curl ; \
    apt-mark auto '.*' > /dev/null; \
    apt-mark manual $savedAptMark

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
	rm -rf /var/lib/apt/lists/*

COPY . .

# Install models.
ENV MODEL=mrm8488/t5-base-finetuned-summarize-news
RUN python install.py

ENV MODEL=google/pegasus-xsum
RUN python install.py

RUN mkdir ~/.streamlit ; \
    cp config.toml ~/.streamlit/config.toml; \
    cp credentials.toml ~/.streamlit/credentials.toml

CMD ["streamlit", "run", "app.py"]
