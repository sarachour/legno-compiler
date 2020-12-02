#include "AnalogLib.h"
extern const char HCDC_DEMO_BOARD;

Fabric::Chip::Tile::Slice::Slice (
	Chip::Tile * parentTile,
	slice sliceId,
	unsigned char ardAnaDiffChan
) :
	parentTile (parentTile),
	sliceId (sliceId),
	ardAnaDiffChan (ardAnaDiffChan)
{
	chipInput = new ChipInput (this);
	tally_dyn_mem <ChipInput> ("ChipInput");

	tileInps = new TileInOut[4] {
		TileInOut(this, tileInp0),
		TileInOut(this, tileInp1),
		TileInOut(this, tileInp2),
		TileInOut(this, tileInp3)
	};
	tally_dyn_mem <TileInOut[4]> ("TileInOut[4]");

	muls = new Multiplier[2] {
		Multiplier (this, unitMulL),
		Multiplier (this, unitMulR)
	};
	tally_dyn_mem <Multiplier[2]> ("Multiplier[2]");

	dac = new Dac (this);
	tally_dyn_mem <Dac> ("Dac");

	integrator = new Integrator (this);
	tally_dyn_mem <Integrator> ("Integrator");

	fans = new Fanout[2] {
		Fanout (this, unitFanL),
		Fanout (this, unitFanR)
	};
	tally_dyn_mem <Fanout[2]> ("Fanout[2]");

	if (sliceId==slice0 || sliceId==slice2) {
		adc = new ChipAdc (this);
		tally_dyn_mem <ChipAdc> ("ChipAdc");
		lut = new LookupTable (this);
		tally_dyn_mem <LookupTable> ("LookupTable");
	}

	tileOuts = new TileInOut[4] {
		TileInOut(this, tileOut0),
		TileInOut(this, tileOut1),
		TileInOut(this, tileOut2),
		TileInOut(this, tileOut3)
	};
	tally_dyn_mem <TileInOut[4]> ("TileInOut[4]");

	chipOutput = new ChipOutput (this, ardAnaDiffChan);
	tally_dyn_mem <ChipOutput> ("ChipOutput");
}

Fabric::Chip::Tile::Slice::~Slice () {
	delete chipInput;
	delete[] tileInps;
	delete dac;
	delete[] muls;
	delete integrator;
	delete[] fans;
	if (sliceId==slice0 || sliceId==slice2) {
		delete adc;
		delete lut;
	}
	delete[] tileOuts;
	delete chipOutput;
};
int slice_to_int(const slice slc){
  switch(slc){
  case slice0: return 0; break;
  case slice1: return 1; break;
  case slice2: return 2; break;
  case slice3: return 3; break;
  }
  error("unknown slice");
  return -1;
}

void Fabric::Chip::Tile::Slice::defaults () {
  dac->defaults();
	fans[0].defaults();
	fans[1].defaults();
  muls[0].defaults();
  muls[1].defaults();
  integrator->defaults();

  if (sliceId == slice0 || sliceId == slice2) {
    adc->defaults();
    lut->defaults();
  }
}
