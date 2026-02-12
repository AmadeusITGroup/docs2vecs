ARG SOURCE_IMAGE_NAME=ubi9/ubi
FROM registry.access.redhat.com/${SOURCE_IMAGE_NAME}:latest

ARG TARGETPLATFORM
ARG TARGETARCH

COPY ./etc/ca-bundle.crt /etc/pki/ca-trust/source/anchors/
COPY ./ /tmp/build

RUN echo "sslverify=0" >> /etc/dnf/dnf.conf \
    && dnf install -y openssl ca-certificates gcc git \
    && if [ "$TARGETPLATFORM" ==  "linux/arm64" ]; then\
        # Creating symlink to /usr/bin/aarch64-linux-gnu-gcc as it is assumed by cython(perhaps worth logging an issue with them)
        ln -sf /usr/bin/gcc /usr/bin/aarch64-linux-gnu-gcc;\
       fi \
    # Remove the insecure setting after install:
    && sed -i '/sslverify=0/d' /etc/dnf/dnf.conf \
    && update-ca-trust extract 

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && source $HOME/.local/bin/env \
    && uv python install 3.11 \
    && uv venv \
    && cd /tmp/build \
    && uv --native-tls pip install --no-cache --override /tmp/build/etc/uv-overrides.txt . \
    && uv --native-tls run --script /tmp/build/etc/fetchDefaultModels.py \
    && rm -rf /tmp/build

ENTRYPOINT ["/root/.local/bin/uv", "--native-tls", "run", "docs2vecs"]
