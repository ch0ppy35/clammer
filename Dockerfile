FROM python:3.12-alpine

ENV CLAM_DIR=/clamav
WORKDIR /clamav-mirror

COPY requirements.txt .
RUN pip install -r requirements.txt
RUN cvd config set --dbdir ${CLAM_DIR}
COPY main.py .

VOLUME ${CLAM_DIR}
CMD python main.py
