FROM python:3.11-slim

# Install system dependencies & build tools untuk whisper.cpp & ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirement & build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build whisper.cpp binary jika belum ter-build
RUN cd whisper.cpp && rm -rf build && cmake -B build && cmake --build build --config Release -j$(nproc)

CMD ["python", "-u", "-m", "agents.agent_loop"]