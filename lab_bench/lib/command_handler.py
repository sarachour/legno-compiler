import lab_bench.lib.command as cmd
import sys



def read_script(filename):
    with open(filename,'r') as fh:
        for idx,line in enumerate(fh):
            if line == "quit":
                sys.exit(0)
            elif line.strip() == "":
                continue

            print(line)
            if line.startswith("#"):
                continue

            command_obj = cmd.parse(line)
            if command_obj is None:
                print("<unknown command: (%s)>" % line)
                raise Exception("command failed")

            if not command_obj.test():
                print("[error] %s" % command_obj.error_msg())
                raise Exception("command failed")

            if not isinstance(command_obj,cmd.Command):
                print("not command")
                raise Exception("command failed")

            yield command_obj



def main_stdout(state):
    while True:
        line = input("ardc>> ")
        if line == "quit":
            sys.exit(0)
        elif line.strip() == "":
            continue

        execute(state,line)


def main_dump_db(state):
    keys = {}
    for data in state.state_db.get_all():
        key = (data.block,data.loc)
        if not data.calib_obj in keys:
            keys[data.calib_obj] = {}

        if not key in keys[data.calib_obj]:
            keys[data.calib_obj][key] = data

    for calib_obj,ds in keys.items():
        for _,obj in ds.items():
            obj.write_dataset(state.state_db)


def main_script_profile(state,filename, \
                        clear=False):
    for command_obj in read_script(filename):
        succ = cmd.profile(state,command_obj, \
                           clear=clear)


def main_script_calibrate(state,filename, \
                          calib_obj,
                          recompute=False):
    successes = []
    failures = []
    for command_obj in read_script(filename):
        cmd.calibrate(state,command_obj, \
                             recompute=recompute,
                             calib_obj=calib_obj)

    return True

def main_script(state,filename):
    for command_obj in read_script(filename):
        command_obj.execute(state)


