def emit_cast(var):
    return "{}({})".format(type(var).__name__, repr(var))
