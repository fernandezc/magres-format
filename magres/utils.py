import os

def insideout():
  """
    Count up in positive numbers and down in negative numbers
  """

  yield 0

  i = 1

  while True:
    yield i
    yield -i
    i += 1

def find_all_magres(dir):
  calcs = []
  for f in os.listdir(dir):
    path = os.path.join(dir, f)
    if ".magres" in f:
      calcs.append(path)
    elif os.path.isdir(path):
      calcs += find_all_magres(path)
  
  return calcs

class lazyproperty(object):
  '''
    Meant to be used for lazy evaluation of an object attribute.
    Property should represent non-mutable data, as it replaces itself.
  '''

  def __init__(self,fget):
    self.fget = fget
    self.func_name = fget.__name__

  def __get__(self,obj,cls):
    # When the property on the owner instance is first accessed we 
    # calculate its value and self-modify to insert the value on 
    # the owner instance
    if obj is None:
      return None
    value = self.fget(obj)
    setattr(obj,self.func_name,value)
    return value