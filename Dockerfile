FROM python:3.7

WORKDIR /opt/requirements
ADD requirements.txt .
RUN pip install -r requirements.txt
RUN pip install \
    gevent==1.4.0 \
    greenlet==0.4.15 \
    gunicorn==20.0.4

ADD interstate_love_song.SimpleWebserviceMapper /opt/SimpleWebserviceMapper
WORKDIR /opt/SimpleWebserviceMapper
RUN python setup.py install

WORKDIR /opt/interstate_love_song
ADD source .

EXPOSE 60443
CMD ["python", "-m", "interstate_love_song"]