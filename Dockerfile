# Ultroid Optimized — Dockerfile
# Supports: docker build -t ultroid . && docker run --env-file .env ultroid

FROM python:3.11-slim

# Metadata
LABEL maintainer="itswill00 <https://github.com/itswill00>"
LABEL description="Ultroid Optimized — Secure & Lightweight Telegram Userbot"

# Set timezone (ganti sesuai kebutuhan, contoh: Asia/Jakarta)
ENV TZ=Asia/Jakarta
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    mediainfo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for Docker cache optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Run bot
CMD ["python3", "-m", "pyUltroid"]
