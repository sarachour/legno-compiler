import sys
import os
import shutil
import glob
import zipfile

def archive_dir(zipname,rootdir,paths):
    zipf = zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED)

    for path in paths:
        for root,dirs,files in  \
            os.walk("%s/%s" % (rootdir,path)):
            for filename in files:
                src_path = "%s/%s" % (root,filename)
                rel_path = src_path.split(rootdir)[1]
                zipf.write(src_path,rel_path)

    zipf.close()


if not (len(sys.argv) == 2):
    raise Exception("usage: pack_char_data <model_number>")

model= sys.argv[1]

tmpdir = 'tmp'
if os.path.exists(tmpdir):
    shutil.rmtree(tmpdir)
os.mkdir(tmpdir)

print("---- copying device state ----")
devstate_dir = "{tmp}/device-state/".format(tmp=tmpdir)
os.makedirs(devstate_dir)
# copy all device state information
base = 'device-state/hcdcv2'
path1 = "{base}/{model_number}*".format(base=base,model_number=model)
path2 = "{base}/*/{model_number}*".format(base=base,model_number=model)
for path in [path1,path2]:
   for filename in glob.glob(path,recursive=True):
    print(filename)
    basefile = filename.split(base)[1]
    dest = "{tmp}/{basefile}".format(tmp=devstate_dir, \
                                     basefile=basefile)
    if not os.path.exists(dest):
        shutil.copytree(filename,dest)

# copy all of the logs
print("---- copying logs ----")
log_dir = "{tmp}/logs".format(tmp=tmpdir)
os.makedirs(log_dir)
path = "*{model_number}.log".format(model_number=model)
for filename in glob.glob(path,recursive=True):
     dest = "{tmp}/{basefile}".format(tmp=log_dir, \
                                      basefile=filename)
     shutil.copy(filename,dest)


print("---- copying execution results ----")
bmark_dir = "{tmp}/bmarks".format(tmp=tmpdir)
path = 'outputs/legno/unrestricted/'
subdirs = ['lgraph-adp/*.adp', \
           'lgraph-diag/*.gv*', \
           'lscale-adp/*{model_number}.adp', \
           'lscale-diag/*{model_number}.dot*', \
           'out-waveform/*_{model_number}_*.json', \
           'plots/wave/*_{model_number}_*.pdf']

for this_bmark_dir in glob.glob(path+"*",recursive=False):
    n_files = 0
    for subpath in subdirs:
        full_glob = "{bmark_dir}/{glob}".format( \
                                                 bmark_dir=this_bmark_dir,  \
                                                 glob=subpath.format(model_number=model))
        for filename in glob.glob(full_glob):
            basefile = filename.split(path)[1]
            dest_file = "{bmark_dir}/{basefile}".format(bmark_dir=bmark_dir, \
                                                       basefile=basefile)
            dest_dir = os.path.dirname(dest_file)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            shutil.copy(filename,dest_file)


print("---- archiving data ----")
archive_dir('{model_number}-devstate.zip'.format(model_number=model), \
            'tmp/', ['logs','device-state'])

archive_dir('{model_number}-bmarks.zip'.format(model_number=model), \
            'tmp/', ['bmarks'])
 

shutil.rmtree(tmpdir)
