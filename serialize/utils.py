

def has_natural_key(content):
    model = content.__class__
    return getattr(content, 'natural_key', None) and getattr(model.objects, 'get_by_natural_key', None)
