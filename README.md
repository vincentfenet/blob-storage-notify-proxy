# Blob Storage Notify Proxy

[![Docker Image](https://badgen.net/badge/icon/docker?icon=docker&label)](https://hub.docker.com/r/vincentfenet/blob-storage-notify-proxy)

This is a simple proxy server that forwards requests to a target server and sends notifications when the request is processed.

## Standalone usage

1. **Set Environment Variables**:
   - `PROXY_PORT`: The port on which the proxy server will listen.
   - `TARGET_SERVER`: The URL of the target server.
   - `NOTIFICATION_ENDPOINT`: The endpoint where notifications will be sent.

2. **Run the Proxy Server**:

```
python proxy_server.py <transformer_module>
```
`transformer_module`: The module that will transform the request before forwarding it to the target server.

## Docker usage

Example of `docker-compose.yml`:
```
services:
  azurite:
    image: mcr.microsoft.com/azure-storage/azurite:3.33.0
  azurite-proxy:
    image: vincentfenet/blob-storage-notify-proxy:1.1
    command: ["azurite-to-azure-event-grid"]
    environment:
      - PROXY_PORT=10001
      - TARGET_SERVER=http://azurite:10000
      - NOTIFICATION_ENDPOINT=http://<your-endpoint>
```