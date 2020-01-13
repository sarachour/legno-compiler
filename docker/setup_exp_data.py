import os
import sys
import shutil

usage = "setup_exp_driver backup|restore|install"
if len(sys.argv) != 2:
    print(usage)
    sys.exit(1)

operation = sys.argv[1]

backup_dir = "outputs/local-results"
osc_data = "oscilloscope_data.zip"

if operation == "backup":
  if os.path.exists(backup_dir):
    print("backup directory already exists...")
    print("path: %s" % backup_dir);
    print("[remove and run backup again]")
    sys.exit(1)

  os.mkdir(backup_dir)
  for filename in ['experiments.db','logs','legno']:
    src_path = "outputs/%s" % filename
    dest_path = "%s/%s" % (backup_dir,filename)
    print("backup %s" % src_path)
    if os.path.exists(src_path):
      shutil.move(src_path, \
                  dest_path)

elif operation == "restore":
  if not os.path.exists(backup_dir):
    print("backup directory doesn't exist...")
    print("path: %s" % backup_dir);
    sys.exit(1)

  for filename in ['experiments.db','logs','legno']:
    src_path = "%s/%s" % (backup_dir,filename)
    dest_path = "outputs/%s" % filename
    if os.path.exists(src_path):
      try:
        shutil.rmtree(dest_path)
        print("clear %s" % dest_path)
      except:
        pass

      print("restore %s" % dest_path)
      shutil.move(src_path, \
                  dest_path)
  if len(os.listdir(backup_dir) ) == 0:
    print("delete %s" % backup_dir)
    shutil.rmtree(backup_dir)
  else:
    print("could not remove <%s>: not empty");

elif operation == "install":
  # test to see that data exists
  if not os.path.exists(osc_data):
    raise Exception("cannot find dataset: <%s>" % osc_data)

  print("oscilloscope data found.")
  cmd = "unzip %s -d outputs/" % osc_data
  print(cmd)
  os.system(cmd);
  try:
    shutil.rmtree("output/__MACOSX")
    print("clear MACOSX files")
  except:
    pass


else:
  print(usage)
  sys.exit(1)


    
