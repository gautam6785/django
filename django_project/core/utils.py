def unpack(kwargs, *args):
  """
  Utility function for retrieving desired values from a kwargs dict.
  """
  ret = []
  for arg in args:
    ret.append(kwargs.get(arg, None))
  return tuple(ret)
