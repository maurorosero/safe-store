# SPDX-License-Identifier: MIT
ARG BUILD_FROM
FROM ${BUILD_FROM}

ARG TARGETARCH
ARG SOPS_VERSION=3.9.4
ARG AGE_VERSION=1.2.0

RUN apk add --no-cache curl \
    && case "${TARGETARCH}" in \
         amd64) sops_arch=amd64; age_arch=linux-amd64 ;; \
         arm64) sops_arch=arm64; age_arch=linux-arm64 ;; \
         *) echo "arquitectura no soportada: ${TARGETARCH}" >&2; exit 1 ;; \
       esac \
    && curl -sSL -o /usr/local/bin/sops \
         "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.linux.${sops_arch}" \
    && curl -sSL -o /usr/local/bin/age \
         "https://github.com/FiloSottile/age/releases/download/v${AGE_VERSION}/age-v${AGE_VERSION}-${age_arch}.tar.gz" \
    && chmod +x /usr/local/bin/sops \
    && mkdir -p /tmp/age && tar -xzf /usr/local/bin/age -C /tmp/age \
    && cp /tmp/age/age/age /tmp/age/age/age-keygen /usr/local/bin/ \
    && rm -rf /tmp/age /usr/local/bin/age \
    && sops --version && age --version

COPY server.py /server.py
CMD ["python3", "-u", "/server.py"]
