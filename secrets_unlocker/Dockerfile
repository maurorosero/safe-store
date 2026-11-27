# SPDX-License-Identifier: MIT
# El Supervisor no siempre pasa BUILD_FROM: el default cubre el build local en
# amd64, y build.yaml / el CI pasan la base correcta por arquitectura.
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

ARG TARGETARCH=amd64
ARG SOPS_VERSION=3.9.4
ARG AGE_VERSION=1.2.0

RUN apk add --no-cache python3 curl \
    && case "${TARGETARCH}" in \
         amd64) sops_arch=amd64; age_arch=linux-amd64 ;; \
         arm64) sops_arch=arm64; age_arch=linux-arm64 ;; \
         *) echo "arquitectura no soportada: ${TARGETARCH}" >&2; exit 1 ;; \
       esac \
    && curl -sSL -o /usr/local/bin/sops \
         "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.linux.${sops_arch}" \
    && curl -sSL -o /tmp/age.tar.gz \
         "https://github.com/FiloSottile/age/releases/download/v${AGE_VERSION}/age-v${AGE_VERSION}-${age_arch}.tar.gz" \
    && chmod +x /usr/local/bin/sops \
    && mkdir -p /tmp/age && tar -xzf /tmp/age.tar.gz -C /tmp/age \
    && cp /tmp/age/age/age /tmp/age/age/age-keygen /usr/local/bin/ \
    && rm -rf /tmp/age /tmp/age.tar.gz \
    && python3 --version && sops --version && age --version

COPY server.py /server.py

# La base de Home Assistant arranca con s6-overlay: un CMD suelto no se ejecuta.
# El servicio se declara como longrun para que s6 lo levante y lo vigile.
RUN mkdir -p /etc/s6-overlay/s6-rc.d/unlocker/dependencies.d \
    && echo longrun > /etc/s6-overlay/s6-rc.d/unlocker/type \
    && printf '#!/usr/bin/with-contenv sh\nexec /usr/bin/python3 -u /server.py\n' \
         > /etc/s6-overlay/s6-rc.d/unlocker/run \
    && chmod +x /etc/s6-overlay/s6-rc.d/unlocker/run \
    && touch /etc/s6-overlay/s6-rc.d/unlocker/dependencies.d/base \
    && mkdir -p /etc/s6-overlay/s6-rc.d/user/contents.d \
    && touch /etc/s6-overlay/s6-rc.d/user/contents.d/unlocker
