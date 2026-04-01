def build_bundle(resources):
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": r} for r in resources
        ]
    }