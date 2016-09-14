from re import match
from string import split

class Version(object):
  def __init__(self, version):
    if match(r'[\d]+(\.[\d]+)+', version):
      strSequence = split(version, '.')
      self.sequence = [int(n) for n in strSequence]
    else:
      raise ValueError('Could not parse version sequence from argument %s' % version)

  def __str__(self):
    return '.'.join([str(n) for n in self.sequence])

  def __lt__(self, other):
    for idx in range(max(len(self.sequence), len(other.sequence))):
      l = self.sequence[idx] if idx < len(self.sequence) else 0
      r = other.sequence[idx] if idx < len(other.sequence) else 0
      if l < r:
        return True
      elif l > r:
        return False
    return False

  def __gt__(self, other):
    for idx in range(max(len(self.sequence), len(other.sequence))):
      l = self.sequence[idx] if idx < len(self.sequence) else 0
      r = other.sequence[idx] if idx < len(other.sequence) else 0
      if l < r:
        return False
      elif l > r:
        return True
    return False

  def __le__(self, other):
    for idx in range(max(len(self.sequence), len(other.sequence))):
      l = self.sequence[idx] if idx < len(self.sequence) else 0
      r = other.sequence[idx] if idx < len(other.sequence) else 0
      if l < r:
        return True
      elif l > r:
        return False
    return True

  def __ge__(self, other):
    for idx in range(max(len(self.sequence), len(other.sequence))):
      l = self.sequence[idx] if idx < len(self.sequence) else 0
      r = other.sequence[idx] if idx < len(other.sequence) else 0
      if l < r:
        return False
      elif l > r:
        return True
    return True

  def __eq__(self, other):
    for idx in range(max(len(self.sequence), len(other.sequence))):
      l = self.sequence[idx] if idx < len(self.sequence) else 0
      r = other.sequence[idx] if idx < len(other.sequence) else 0
      if l < r:
        return False
      elif l > r:
        return False
    return True

  def __ne__(self, other):
    for idx in range(max(len(self.sequence), len(other.sequence))):
      l = self.sequence[idx] if idx < len(self.sequence) else 0
      r = other.sequence[idx] if idx < len(other.sequence) else 0
      if l < r:
        return True
      elif l > r:
        return True
    return False
