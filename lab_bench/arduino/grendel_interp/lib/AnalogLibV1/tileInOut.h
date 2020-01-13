#include "AnalogLib.h"

class Fabric::Chip::Tile::Slice::TileInOut : public Fabric::Chip::Tile::Slice::FunctionUnit {
	friend Slice;

	TileInOut ( Slice * parentSlice, unit unitId_ ) : FunctionUnit(parentSlice, unitId_) {
		in0 = new Interface (this, in0Id);
		tally_dyn_mem <Interface> ("Interface");
		out0 = new Interface (this, out0Id);
		tally_dyn_mem <Interface> ("Interface");
	};
	~TileInOut() override {
		delete in0;
		delete out0;
	};

};
