FROM debian:bookworm

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install basic tools useful for rootfs creation
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        debootstrap \
        xz-utils \
        ca-certificates \
        gnupg \
        wget \
        curl \
        tar \
        sudo && \
    rm -rf /var/lib/apt/lists/*

# Default workspace
WORKDIR /work

# Optional: Entry into a shell
CMD ["/bin/bash"]