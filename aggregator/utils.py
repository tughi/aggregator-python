def signed_long(value):
    if isinstance(value, basestring):
        value = int(value)

    # convert to signed 64bit signed
    value &= 0xFFFFFFFFFFFFFFFF
    if value > 0x7FFFFFFFFFFFFFFF:
        value -= 0x10000000000000000
    return value


