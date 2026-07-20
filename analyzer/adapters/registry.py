ADAPTERS = []

def register_adapter(detector, adapter):
    """
    Register a new adapter
    """
    ADAPTERS.append((detector, adapter))


def get_adapter(data):
    """
    Find adapter that can handle the given report format
    """
    for detector, adapter in ADAPTERS:

        try:
            if detector(data):
                return adapter
        except Exception:
            continue

    return None