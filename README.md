# Blob Storage Notify Proxy

This is a simple proxy server that forwards requests to a target server and sends notifications when the request is processed.

## Usage

1. **Set Environment Variables**:
   - `PROXY_PORT`: The port on which the proxy server will listen.
   - `TARGET_SERVER`: The URL of the target server.
   - `NOTIFICATION_ENDPOINT`: The endpoint where notifications will be sent.

2. **Run the Proxy Server**:

```
python proxy_server.py <transformer_module>
```
`transformer_module`: The module that will transform the request before forwarding it to the target server.
