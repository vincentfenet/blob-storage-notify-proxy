"""Transform the data into a format suitable for Azure Event Grid."""

# pragma pylint: disable=invalid-name

import datetime
import os

CONFIG_PROXY_PORT = int(os.getenv("PROXY_PORT"))


def transform(data):
    """Transform the data into a format suitable for Azure Event Grid."""
    res = []
    for item in data:
        if (
            item["request"]["method"] == "PUT"
            and item["response"]["status_code"] == 201
        ):
            parts = item["request"]["path"].strip("/").split("/", maxsplit=2)
            res.append(
                {
                    "topic": "",
                    "subject": "",
                    "eventType": "Microsoft.Storage.BlobCreated",
                    "id": "",
                    "data": {
                        "api": "PutBlob",
                        "requestId": "",
                        "eTag": "",
                        "contentType": "application/octet-stream",
                        "contentLength": 16,
                        "blobType": "BlockBlob",
                        "accessTier": "Default",
                        "url": f"http://{parts[0]}.blob.local:{CONFIG_PROXY_PORT}/{parts[1]}/"
                        + parts[2].split("?")[0],
                        "sequencer": "",
                        "storageDiagnostics": {"batchId": ""},
                    },
                    "dataVersion": "",
                    "metadataVersion": "1",
                    "eventTime": datetime.datetime.now().isoformat() + "Z",
                }
            )
    return res
