FROM python:3.9-slim

# Install system dependencies including PulseAudio
RUN apt-get update && apt-get install -y \
    python3-dev \
    build-essential \
    libssl-dev \
    python3-pip \
    git \
    pulseaudio \
    alsa-utils \
    libasound2-dev \
    wget \
    libpulse-dev \
    portaudio19-dev \
    ffmpeg \
    libavcodec-extra \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Download and install PJSIP
WORKDIR /tmp
RUN wget https://github.com/pjsip/pjproject/archive/refs/tags/2.14.1.tar.gz && \
    tar -xf 2.14.1.tar.gz && \
    cd pjproject-2.14.1 && \
    export CFLAGS="$CFLAGS -fPIC -DPJMEDIA_AUDIO_DEV_HAS_PORTAUDIO=1" && \
    ./configure --enable-shared \
                --with-external-pa \
                --enable-ext-sound \
                --disable-speex-codec \
                --disable-speex-aec \
                --disable-l16-codec \
                --disable-gsm-codec \
                --disable-g722-codec \
                --disable-g7221-codec \
                --disable-ilbc-codec && \
    make dep && make clean && make && make install && \
    ldconfig && \
    cd pjsip-apps/src && \
    git clone https://github.com/mgwilliams/python3-pjsip.git && \
    cd python3-pjsip && \
    python3 setup.py build && \
    python3 setup.py install

# Create a non-root user
RUN useradd -m appuser && \
    mkdir -p /home/appuser/app && \
    chown -R appuser:appuser /home/appuser

# Set up PulseAudio configuration
RUN mkdir -p /etc/pulse
COPY pulse-client.conf /etc/pulse/client.conf
RUN mkdir -p /home/appuser/.config/pulse && \
    cp /etc/pulse/client.conf /home/appuser/.config/pulse/ && \
    chown -R appuser:appuser /home/appuser/.config

# Set up ALSA configuration for better audio handling
RUN echo "pcm.!default {\n\
    type pulse\n\
    fallback \"sysdefault\"\n\
    hint {\n\
        show on\n\
        description \"PulseAudio Sound Server\"\n\
    }\n\
}\n\
\n\
ctl.!default {\n\
    type pulse\n\
    fallback \"sysdefault\"\n\
}\n\
\n\
pcm.pulse {\n\
    type pulse\n\
}\n\
\n\
ctl.pulse {\n\
    type pulse\n\
}" > /etc/asound.conf

# Add PulseAudio debug script
RUN echo '#!/bin/bash\n\
echo "Starting PulseAudio in debug mode..."\n\
pulseaudio --start --log-level=4 --verbose --exit-idle-time=-1\n\
pactl list short sinks\n\
' > /home/appuser/app/pulseaudio_debug.sh && \
    chmod +x /home/appuser/app/pulseaudio_debug.sh

# Create PulseAudio startup script
RUN echo '#!/bin/bash\n\
echo "Starting PulseAudio..."\n\
mkdir -p /run/user/1000/pulse\n\
pulseaudio --start --log-level=4 --verbose --exit-idle-time=-1 --disallow-exit\n\
sleep 2\n\
echo "Starting SIP application..."\n\
python3 sip_caller.py\n\
' > /home/appuser/app/start.sh && \
    chmod +x /home/appuser/app/start.sh

WORKDIR /home/appuser/app

# Copy application files
COPY sip_caller.py .
COPY .env .

USER appuser

# Set PulseAudio environment variables
ENV PULSE_SERVER=unix:/tmp/pulseaudio.socket
ENV PULSE_COOKIE=/tmp/pulseaudio.cookie
ENV PULSE_LATENCY_MSEC=30
ENV PULSE_LOG_LEVEL=4

# Set the entry point to run sip_caller.py directly
CMD ["python3", "sip_caller.py"]
