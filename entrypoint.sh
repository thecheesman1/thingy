#!/bin/bash

# 1. Start the Virtual Display (Matching Aethel OS's 900x700 resolution)
Xvfb :0 -screen 0 900x700x24 &
sleep 2

# 2. Start the VNC Server (binds to the virtual display)
x11vnc -display :0 -nopw -listen localhost -xkb -forever &

# 3. Start noVNC (Translates VNC into a Webpage on port 8080)
websockify --web=/usr/share/novnc/ 8080 localhost:5900 &

# 4. Start Aethel OS!
echo "Booting Aethel OS..."
python /app/main.py
