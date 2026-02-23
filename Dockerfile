FROM python:3.11-slim

# Prevent apt-get from prompting for input
ENV DEBIAN_FRONTEND=noninteractive

# Install Virtual Screen (Xvfb), VNC, and Pygame dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-ttf-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Pygame
RUN pip install pygame

# Copy your OS code and the startup script
COPY aethel_os_nexus.py /app/main.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set the virtual display environment variable
ENV DISPLAY=:0

# Expose the web interface port
EXPOSE 8080

CMD ["/app/entrypoint.sh"]
