from dslang.dsprog import DSProgDB
import importlib.util
import os

def dynamic_load(filepath):
  spec = importlib.util.spec_from_file_location("module.name",
                                                filepath)
  module = importlib.util.module_from_spec(spec)
  try:
    obj = spec.loader.exec_module(module)
  except FileNotFoundError as e:
    print("file not found: %s" % filepath)
    return

  if hasattr(module, "dssim") and \
     hasattr(module, "dsprog") and \
     hasattr(module, "dsinfo") and \
     hasattr(module, "dsname"):
    DSProgDB.register(module.dsname(), \
                      module.dsprog, \
                      module.dssim, \
                      module.dsinfo)


root_dir = os.path.dirname(os.path.abspath(__file__))
for root, dirs, files in os.walk(root_dir):
   for filename in files:
     if filename.endswith(".py") and \
        filename != "__init__.py":
       dynamic_load("%s/%s" % (root,filename))

