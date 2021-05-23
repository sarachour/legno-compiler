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


def compile_it(program):
  lexec_cmd = "python3 -u legno.py lexec {program}"
  lwav_cmd = "python3 -u legno.py lwav {program} "+ \
    "--individual-plots --summary-plots"

  cmd = lexec_cmd.format(program=program)
  return_code,_ = execute_cmd(cmd)
  if return_code != 0:
    raise Exception("[ERROR] Failed to execute application on HCDC. <lexec> returned %d" % return_code)

  cmd = lwav_cmd.format(program=program)
  return_code,_ = execute_cmd(cmd)
  if return_code != 0:
    raise Exception("[ERROR] Failed to execute application on HCDC. <lexec> returned %d" % return_code)



parser = argparse.ArgumentParser(description='synthesize graphs for and scale application.')
parser.add_argument('program', help="name of program to run. Program must be in progs/ directory")

args = parser.parse_args()

compile_it(args.program)
