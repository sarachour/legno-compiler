import os
benchmarks = ["cos", \
        "cosc", \
        "spring", \
        "pend", \
        "vanderpol", \
        "forced", \
        "bont", \
        "gentoggle", \
        "pid", \
        "kalconst", \
        "smmrxn", \
        "heatN4X2"]

modes = ["default_maxfit_naive", \
        "default_minerr_naive", \
        "default_maxfit", \
        "default_minerr", \
]

heat_modes = [
        "default_maxfit_naive", \
        "default_minerr_naive", \
        "default_maxfit_heat", \
        "default_minerr_heat", \
]

for bmark in benchmarks:
    this_mode = modes if not "heat" in bmark else heat_modes
    for idx,mode in enumerate(this_mode):
        flag = ""
        if idx == 0:
            flag="--lgraph"

        cmd = "time python3 legno_runner.py --config configs/{config}.cfg {bmark} {flag} --ignore-missing"
        conc_cmd = cmd.format(config=mode,bmark=bmark,flag=flag)
        print("echo %s" % conc_cmd);
        print("%s  > /dev/null 2>&1" % conc_cmd);



