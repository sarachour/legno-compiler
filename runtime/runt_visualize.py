
def visualize(args):
    board = get_device(args.model_number,layout=True)
    label = physutil.DeltaModelLabel(args.method)
    ph = paths.DeviceStatePathHandler(board.name, \
                                      board.model_number,make_dirs=True)

    for expmodel in physapi.get_all(board.physdb,board):
        if expmodel.delta_model.complete:
            png_file = ph.get_delta_vis(expmodel.block.name, \
                                        str(expmodel.loc), \
                                        str(expmodel.output.name), \
                                        str(expmodel.static_cfg), \
                                        str(expmodel.hidden_cfg), \
                                        expmodel.delta_model.label)
            vizlib.deviation(expmodel, \
                             png_file, \
                             baseline=vizlib.ReferenceType.MODEL_PREDICTION, \
                             num_bins=10, \
                             amplitude=None, \
                             relative=True)
