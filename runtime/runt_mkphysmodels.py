
def update_dectree_data(blk,loc,exp_mdl, \
                        metadata, \
                        params, \
                        model_errors, \
                        hidden_code_fields, \
                        hidden_code_bounds, \
                        hidden_codes):

    key = (blk.name,exp_mdl.static_cfg)
    if not key in params:
        params[key] = {}
        metadata[key] = (blk,exp_mdl.cfg)
        model_errors[key] = []
        hidden_codes[key] = []
        hidden_code_fields[key] = []
        hidden_code_bounds[key] = {}

    for par,value in exp_mdl.delta_model.params.items():
        if not par in params[key]:
            params[key][par] = []

        params[key][par].append(value)

    for hidden_code,_ in exp_mdl.hidden_codes():
        if not hidden_code in hidden_code_fields[key]:
            hidden_code_bounds[key][hidden_code] = (blk.state[hidden_code].min_value, \
                                                    blk.state[hidden_code].max_value)
            hidden_code_fields[key].append(hidden_code)

    entry = [0]*len(hidden_code_fields[key])
    for hidden_code,value in exp_mdl.hidden_codes():
        idx = hidden_code_fields[key].index(hidden_code)
        entry[idx] = value

    hidden_codes[key].append(entry)
    model_errors[key].append(exp_mdl.delta_model.model_error)

def mktree(args):
    dev = get_device(args.model_number,layout=True)
    params = {}
    metadata = {}
    hidden_codes = {}
    hidden_code_fields = {}
    hidden_code_bounds = {}
    model_errors = {}
    for exp_mdl in physapi.get_all(dev.physdb,dev):
        blk = exp_mdl.block
        if len(exp_mdl.dataset) == 0:
            continue

        if not exp_mdl.delta_model.complete:
            fitlib.fit_delta_model(exp_mdl)

        if not exp_mdl.delta_model.complete:
            print("[WARN] incomplete delta model!")
            continue

        update_dectree_data(blk,exp_mdl.loc,exp_mdl, \
                            metadata,params,model_errors, \
                            hidden_code_fields, \
                            hidden_code_bounds, \
                            hidden_codes)

    for key in model_errors.keys():
        blk,cfg = metadata[key]
        n_samples = len(model_errors[key])
        min_size = round(n_samples/args.num_leaves)
        print("--- fitting decision tree (%d samples) ---" % n_samples)
        hidden_code_fields_ = hidden_code_fields[key]
        hidden_code_bounds_ = hidden_code_bounds[key]
        hidden_codes_ = hidden_codes[key]
        model_errors_ = model_errors[key]

        model = physlib.ExpPhysModel(dev.physdb,dev,blk,cfg)
        model.num_samples = n_samples

        print(cfg)
        dectree,predictions = fit_lindectree.fit_decision_tree(hidden_code_fields_, \
                                                               hidden_codes_, \
                                                               model_errors_, \
                                                               bounds=hidden_code_bounds_, \
                                                               max_depth=args.max_depth, \
                                                               min_size=min_size)
        err = fit_lindectree.model_error(predictions,model_errors_)
        pct_err = err/max(np.abs(model_errors_))*100.0
        print("<<dectree>>: [[Model-Err]] err=%f pct-err=%f param-range=[%f,%f]" \
              % (err, pct_err, \
                 min(model_errors_), \
                 max(model_errors_)))

        model.set_param(physlib.ExpPhysModel.MODEL_ERROR, \
                        dectree)

        for param,param_values in params[key].items():
            assert(len(param_values) == n_samples)
            dectree,predictions = fit_lindectree.fit_decision_tree(hidden_code_fields_, \
                                                                   hidden_codes_, \
                                                                   param_values, \
                                                                   bounds=hidden_code_bounds_, \
                                                                   max_depth=args.max_depth, \
                                                                   min_size=min_size)
            model.set_param(param, dectree)

            err = fit_lindectree.model_error(predictions,param_values)
            pct_err = err/max(np.abs(model_errors_))*100.0
            print("<<dectree>>: [[Param:%s]] err=%f pct-err=%f param-range=[%f,%f]" \
                  % (param, err, pct_err, \
                     min(param_values), \
                     max(param_values)))

        model.update()

