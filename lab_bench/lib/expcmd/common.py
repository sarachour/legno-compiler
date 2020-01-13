import parse as parselib
import lab_bench.lib.cstructs as cstructs
import lab_bench.lib.enums as enums
from lab_bench.lib.base_command import OptionalValue, ArduinoCommand

def build_exp_ctype(exp_data):
    return {
        'test':ArduinoCommand.DEBUG,
        'type':enums.CmdType.EXPERIMENT_CMD.name,
        'data': {
            'exp_cmd':exp_data
        }
    }

def do_parse(cmd,args,ctor):
    line = " ".join(args)
    if cmd == "" or cmd is None:
        full_cmd = ctor.name()
    else:
        full_cmd = " ".join([ctor.name(),cmd])
    result = parselib.parse(full_cmd,line)
    if result is None:
        return OptionalValue.error("usage:[%s]\nline:[%s]" % (full_cmd,line))

    obj = ctor(**result.named)
    return OptionalValue.value(obj)

def strict_do_parse(cmd,args,ctor):
    result = do_parse(cmd,args,ctor)
    if result.success:
        return result.value

    raise Exception(result.message)

