import sys
import os
import shutil
import glob
import zipfile


if not (len(sys.argv) == 2):
    raise Exception("usage: pack_char_data <model_number>")

model= sys.argv[1]

tmpdir = 'tmp'
if os.path.exists(tmpdir):
    shutil.rmtree(tmpdir)
os.mkdir(tmpdir)

print("---- unpacking device state archive ----")
zipname = "{model_number}-devstate.zip".format(model_number=model)
if os.path.exists(zipname):
    zipf = zipfile.ZipFile(zipname,'r',zipfile.ZIP_DEFLATED)
    zipf.extractall(path=tmpdir)


print("---- copying device state ----")
devstate_dir = "{tmp}/device-state/*".format(tmp=tmpdir)
dest_dir = "device-state/hcdcv2"
for filepath in glob.glob(devstate_dir,recursive=True):
    filename = os.path.basename(filepath)
    dest_file = "%s/%s" % (dest_dir,filename)
    if os.path.exists(dest_file):
        shutil.rmtree(dest_file)

    shutil.copytree(filepath,dest_file)


print("---- unpacking benchmark archive ----")
zipname = "{model_number}-bmarks.zip".format(model_number=model)
if os.path.exists(zipname):
    zipf = zipfile.ZipFile(zipname,'r',zipfile.ZIP_DEFLATED)
    zipf.extractall(path=tmpdir)


print("---- copying benchmark data ----")
bmark_dir = "{tmp}/bmarks/".format(tmp=tmpdir)
dest_dir = "outputs/legno/unrestricted"
subdirs = ['lscale-adp/*{model_number}.adp', \
           'lscale-diag/*{model_number}.dot*', \
           'out-waveform/*_{model_number}_*.json', \
           'plots/wave/*_{model_number}_*.pdf']

for subdir in subdirs:
    full_dest_glob = "{bmark_dir}/*/{glob}".format(bmark_dir=dest_dir, \
                                                   glob=subdir.format(model_number=model))
    for filename in glob.glob(full_dest_glob):
        os.remove(filename)

for this_bmark_dir in glob.glob(bmark_dir+"*",recursive=False):
    for subpath in subdirs:
    
        full_src_glob = "{bmark_dir}/{glob}".format( \
                                                 bmark_dir=this_bmark_dir,  \
                                                 glob=subpath.format(model_number=model))


        for filename in glob.glob(full_src_glob):
            basefile = filename.split(bmark_dir)[1]
            dest_file = "{dest_dir}/{filename}".format(dest_dir=dest_dir, \
                                                       filename=basefile)
            this_dest_dir = os.path.dirname(dest_file)
            if not os.path.exists(this_dest_dir):
                os.makedirs(this_dest_dir)

            shutil.copy(filename,dest_file)
