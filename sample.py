"""Sample Python script for transforming data."""

def transform(data):
    """Sample transformation function."""
    res = []
    for item in data:
        if (
            item["request"]["method"] == "PUT"
            and item["response"]["status_code"] == 201
        ):
            parts = item["request"]["path"].strip("/").split("/")
            res.append(
                {
                    "endpoint": parts[0],
                    "container_name": parts[1],
                    "path": '/'.join(parts[2:]).split('?', maxsplit=1)[0],
                }
            )
    return res
