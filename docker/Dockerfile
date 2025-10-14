
# Use an official Ubuntu base image
FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update package list and install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    git-buildpackage \
    sbuild \
    gh \
    debootstrap \
    tree \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Optional: copy your project files
# COPY . .

# Default command
CMD [ "bash" ]
