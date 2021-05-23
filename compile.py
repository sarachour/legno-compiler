import argparse
import os
import subprocess

def execute_command(cmd):
    p = subprocess.Popen(cmd.split(),  \
                        stdout=subprocess.PIPE, \
                        stderr=subprocess.STDOUT)
    out_text = ""
    while True:
      output = p.stdout.readline()
      out_str = output.decode('utf-8')
      if out_str == '' and p.poll() is not None:
        break
      if output:
        print(out_str.strip())
        out_text += out_str

    return p.returncode,out_text

def is_uncalibrated(out):
  for line in out.split("\n"):
    if "Exception:" in line:
      if "no valid modes" in line:
        return True

def compile_it(program,model_number,scale_only=False,num_lgraph=10,num_lscale=10):
  lgraph_cmd = "python3 -u legno.py lgraph {program} --adps {num_lgraph}"
  lscale_cmd = "python3 -u legno.py lscale --model-number {model_number} " + \
    "--objective qtytau --scale-adps {num_lscale} --scale-method phys --calib-obj {calib_obj} {program}"
  lcal_cmd = "python3 -u legno.py lcal --model-number {model_number} {program} {calib_obj_arg}"

  if not scale_only:
    cmd = lgraph_cmd.format(program=program,num_lgraph=num_lgraph)
    ret,out = execute_command(cmd)
    if ret != 0:
      raise Exception("[ERROR] Could not synthesize circuits! lgraph failed with code <%d>" % ret)


  for calib_strat,calib_flag in [('minimize_error','--minimize-error'), \
                      ("maximize_fit",'--maximize-fit')]:
    cmd = lscale_cmd.format(model_number=model_number, num_lscale=num_lscale, \
                            calib_obj=calib_strat, program=program)
    ret,out = execute_command(cmd)

    if ret != 0 and not is_uncalibrated(out):
      raise Exception("[ERROR] Could not scale circuits! lscale failed with code <%d>" % ret)

    elif ret != 0:
      print("[[[ Uncalibrated Analog Blocks!! ]]]")
      print("----------------------------------")
      print("  Could not scale the circuit: there are blocks in use which are uncalibrated")
      print("  The compiler will now automatically calibrate these blocks")
      print("  The HCDCv2 will need to be plugged in for this procedure to work.")
      print("----------------------------------")
      result = input("automatically calibrate the device (y/n)?")
      print("")
      if "y" in result:
        print("===== CALIBRATING DEVICE ===")
        cmd2 = lcal_cmd.format(program=program,calib_obj_arg=calib_flag,model_number=model_number)
        ret,out = execute_command(cmd2)
        if ret != 0:
          raise Exception("[[ Failed to Calibrate the device]]")
        else:
          print("\n\n")
          print("############################")
          print("[[ Calibration Finished!! ]]")
          print("############################")
          print("")
          print("[[Attempting to Scale Circuit Again]]")
          print("")
          ret,out = execute_command(cmd)
          if ret != 0:
            raise Exception("[ERROR] Could not scale circuits! lscale failed with code <%d>" % ret)


      else:
        print("[[ Skipping Calibration ]]")


parser = argparse.ArgumentParser(description='synthesize graphs for and scale application.')
parser.add_argument('program', help="name of program to run. Program must be in progs/ directory")
parser.add_argument('model_number', help="board model number.")
parser.add_argument('--num-circuits',default=10,help="number of circuits to synthesize.")
parser.add_argument('--num-scale-xforms',default=10,help="number of scaling transforms.")
parser.add_argument('--scale-only',action="store_true",help="only scale the existing circuits.")

args = parser.parse_args()

compile_it(args.program,args.model_number, \
           scale_only=args.scale_only,\
           num_lgraph=args.num_circuits, \
           num_lscale=args.num_scale_xforms)
