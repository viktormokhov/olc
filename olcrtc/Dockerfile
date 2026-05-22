# olcrtc:patched — universal-carrier + defer carrier reconnect (Telemost/VP8)
# Build: docker build -t olcrtc:patched -f olcrtc/Dockerfile olcrtc/

FROM golang:1.25-alpine AS builder

RUN apk add --no-cache git ca-certificates python3

ARG OLCRTC_REPO=https://github.com/openlibrecommunity/olcrtc.git
# refactor/universal-carrier was merged; upstream only has master now
ARG OLCRTC_BRANCH=master

WORKDIR /src
RUN git clone --depth 1 --branch "${OLCRTC_BRANCH}" --recurse-submodules "${OLCRTC_REPO}" .

COPY patch_defer_carrier.py /patch/
RUN python3 /patch/patch_defer_carrier.py /src

RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /out/olcrtc ./cmd/olcrtc

# Runtime image aligned with upstream olcrtc docker (YAML config, no legacy socks5 sidecar)
FROM alpine:3.21

RUN apk add --no-cache ca-certificates ffmpeg

COPY --from=builder /out/olcrtc /usr/local/bin/olcrtc
COPY --from=builder /src/script/docker/olcrtc-entrypoint.sh /usr/local/bin/olcrtc-entrypoint
COPY --from=builder /src/script/docker/olcrtc-healthcheck.sh /usr/local/bin/olcrtc-healthcheck
COPY --from=builder /src/data /usr/share/olcrtc/data

RUN chmod +x /usr/local/bin/olcrtc /usr/local/bin/olcrtc-entrypoint /usr/local/bin/olcrtc-healthcheck

ENV OLCRTC_MODE=srv \
    OLCRTC_DATA_DIR=/usr/share/olcrtc/data \
    OLCRTC_DNS=1.1.1.1:53 \
    OLCRTC_KEY_FILE=/var/lib/olcrtc/key.hex

VOLUME ["/var/lib/olcrtc"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s \
  CMD ["/usr/local/bin/olcrtc-healthcheck"]

ENTRYPOINT ["/usr/local/bin/olcrtc-entrypoint"]
