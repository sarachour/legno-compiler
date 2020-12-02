#include "AnalogLib.h"
#include "assert.h"
#include "calib_util.h"

void Fabric::Chip::Tile::Slice::Fanout::computeInterval(fanout_state_t& state,
                          port_type_t port, float& min, float& max){
  float ampl = 2.0;
  if(state.range == RANGE_HIGH){
    ampl = 20.0;
  }
  if(port == in0Id || port == out0Id || port == out1Id || port == out2Id){
    min = -ampl;
    max = ampl;
  }
  else {
    error("fanout was supplied unknown nport");
  }
}

float Fabric::Chip::Tile::Slice::Fanout::computeOutput(fanout_state_t& codes,
                                                       ifc out_id,  \
                                                       float in){
  float sign;
  switch(out_id){
  case out0Id:
  case out1Id:
  case out2Id:
    sign=util::sign_to_coeff(codes.inv[out_id]); break;
  default:
    error("Fanout::compute_out unknown out_id");
  }
  return sign*in;
}
void Fabric::Chip::Tile::Slice::Fanout::setEnable (
	bool enable
) {
	/*record*/
	m_state.enable = enable;
	/*set*/
	setParam0();
	setParam1();
	setParam2();
	setParam3();
}

void Fabric::Chip::Tile::Slice::Fanout::setRange (
	range_t range// 20uA mode
	// 20uA mode results in more ideal behavior in terms of phase shift but consumes more power
	// this setting should match the unit that gives the input to the fanout
) {
  assert(range != RANGE_LOW);
  m_state.range = range;
	setParam0();
	setParam1();
	setParam2();
	setParam3();
}

void Fabric::Chip::Tile::Slice::Fanout::setInv (
                                                ifc port,
                                                bool inverse // whether output is negated
                                                ) {
  if(!(port == out0Id || port == out1Id || port == out2Id)){
    error("unexpected range");
  }
  m_state.inv[port] = inverse;
	setParam1 ();
	setParam2 ();
	setParam3 ();
}

void Fabric::Chip::Tile::Slice::Fanout::setThird (
	bool third // whether third output is on
) {
	m_state.third = third;
	setParam3();
}

void Fabric::Chip::Tile::Slice::Fanout::defaults (){
  m_state.range = RANGE_MED;
  m_state.inv[in0Id] = false;
  m_state.inv[in1Id] = false;
  m_state.inv[out0Id] = false;
  m_state.inv[out1Id] = false;
  m_state.inv[out2Id] = false;
  m_state.port_cal[in0Id] = 0;
  m_state.port_cal[in1Id] = 0;
  m_state.port_cal[out0Id] = 31;
  m_state.port_cal[out1Id] = 31;
  m_state.port_cal[out2Id] = 31;
  m_state.enable = false;
  m_state.third = false;
  m_state.nmos = 0;
  m_state.pmos = 3;
	setAnaIrefNmos();
	setAnaIrefPmos();
}

Fabric::Chip::Tile::Slice::Fanout::Fanout (
	Chip::Tile::Slice * parentSlice,
	unit unitId
) :
	FunctionUnit(parentSlice, unitId)
{
	in0 = new Interface (this, in0Id);
	tally_dyn_mem <Interface> ("GenericInterface");
	out0 = new Interface (this, out0Id);
	tally_dyn_mem <Interface> ("FanoutOut");
	out1 = new Interface (this, out1Id);
	tally_dyn_mem <Interface> ("FanoutOut");
	out2 = new Interface (this, out2Id);
	tally_dyn_mem <Interface> ("FanoutOut");
  defaults();
}

/*Set enable, range*/
void Fabric::Chip::Tile::Slice::Fanout::setParam0 () const {
	unsigned char cfgTile = 0;
  bool is_hi = (m_state.range == RANGE_HIGH);
	cfgTile += m_state.enable ? 1<<7 : 0;
	cfgTile += is_hi ? 1<<5 : 0;
	setParamHelper (0, cfgTile);
}

/*Set calDac1, invert output 1*/
void Fabric::Chip::Tile::Slice::Fanout::setParam1 () const {
	unsigned char calDac1 = m_state.port_cal[out0Id];
	if (calDac1<0||63<calDac1) error ("calDac1 out of bounds");
	unsigned char cfgTile = 0;
	cfgTile += calDac1<<2;
	cfgTile += m_state.inv[out0Id] ? 1<<1 : 0;
	setParamHelper (1, cfgTile);
}

/*Set calDac2, invert output 2*/
void Fabric::Chip::Tile::Slice::Fanout::setParam2 () const {
	unsigned char calDac2 = m_state.port_cal[out1Id];
	if (calDac2<0||63<calDac2) error ("calDac2 out of bounds");
	unsigned char cfgTile = 0;
	cfgTile += calDac2<<2;
	cfgTile += m_state.inv[out1Id] ? 1<<1 : 0;
	setParamHelper (2, cfgTile);
}

/*Set calDac3, invert output 3, enable output 3*/
void Fabric::Chip::Tile::Slice::Fanout::setParam3 () const {
	unsigned char calDac3 = m_state.port_cal[out2Id];
	if (calDac3<0||63<calDac3) error ("calDac3 out of bounds");
	unsigned char cfgTile = 0;
	cfgTile += calDac3<<2;
	cfgTile += m_state.inv[out2Id] ? 1<<1 : 0;
	cfgTile += m_state.third ? 1<<0 : 0;
	setParamHelper (3, cfgTile);
}

/*Helper function*/
void Fabric::Chip::Tile::Slice::Fanout::setParamHelper (
	unsigned char selLine,
	unsigned char cfgTile
) const {
	if (selLine<0||3<selLine) error ("selLine out of bounds");

	/*DETERMINE SEL_ROW*/
	unsigned char selRow;
	switch (parentSlice->sliceId) {
		case slice0: selRow = 2; break;
		case slice1: selRow = 3; break;
		case slice2: selRow = 4; break;
		case slice3: selRow = 5; break;
		default: error ("invalid slice. Only slices 0 through 3 have FANs"); break;
	}

	/*DETERMINE SEL_COL*/
	unsigned char selCol;
	switch (unitId) {
		case unitFanL: selCol = 0; break;
		case unitFanR: selCol = 1; break;
		default: error ("invalid unit. Only unitFanL and unitFanR are FANs"); break;
	}

	Vector vec = Vector (
		*this,
		selRow,
		selCol,
		selLine,
		endian (cfgTile)
	);

	parentSlice->parentTile->parentChip->cacheVec (
		vec
	);
}




void Fabric::Chip::Tile::Slice::Fanout::setAnaIrefNmos () const {
	unsigned char selRow=0;
	unsigned char selCol;
	unsigned char selLine;
  util::test_iref(m_state.nmos);
	switch (unitId) {
		case unitFanL: switch (parentSlice->sliceId) {
			case slice0: selCol=0; selLine=0; break;
			case slice1: selCol=0; selLine=1; break;
			case slice2: selCol=1; selLine=0; break;
			case slice3: selCol=1; selLine=1; break;
			default: error ("FAN invalid slice"); break;
		} break;
		case unitFanR: switch (parentSlice->sliceId) {
			case slice0: selCol=1; selLine=2; break;
			case slice1: selCol=1; selLine=3; break;
			case slice2: selCol=2; selLine=0; break;
			case slice3: selCol=2; selLine=1; break;
			default: error ("FAN invalid slice"); break;
		} break;
		default: error ("FAN invalid unitId"); break;
	}
	unsigned char cfgTile = endian(parentSlice->parentTile->parentChip->cfgBuf[parentSlice->parentTile->tileRowId][parentSlice->parentTile->tileColId][selRow][selCol][selLine]);
	switch (unitId) {
		case unitFanL: switch (parentSlice->sliceId) {
			case slice0: cfgTile = (cfgTile & 0b00000111) + ((m_state.nmos<<3) & 0b00111000); break;
			case slice1: cfgTile = (cfgTile & 0b00000111) + ((m_state.nmos<<3) & 0b00111000); break;
			case slice2: cfgTile = (cfgTile & 0b00111000) + (m_state.nmos & 0b00000111); break;
			case slice3: cfgTile = (cfgTile & 0b00111000) + (m_state.nmos & 0b00000111); break;
			default: error ("FAN invalid slice"); break;
		} break;
		case unitFanR: switch (parentSlice->sliceId) {
			case slice0: cfgTile = (cfgTile & 0b00000111) + ((m_state.nmos<<3) & 0b00111000); break;
			case slice1: cfgTile = (cfgTile & 0b00000111) + ((m_state.nmos<<3) & 0b00111000); break;
			case slice2: cfgTile = (cfgTile & 0b00111000) + (m_state.nmos & 0b00000111); break;
			case slice3: cfgTile = (cfgTile & 0b00111000) + (m_state.nmos & 0b00000111); break;
			default: error ("FAN invalid slice"); break;
		} break;
		default: error ("FAN invalid unitId"); break;
	}

	Vector vec = Vector (
		*this,
		selRow,
		selCol,
		selLine,
		endian (cfgTile)
	);

	parentSlice->parentTile->parentChip->cacheVec (
		vec
	);
}

void Fabric::Chip::Tile::Slice::Fanout::setAnaIrefPmos () const {

	unsigned char selRow=0;
	unsigned char selCol;
	unsigned char selLine;
  util::test_iref(m_state.pmos);
	switch (unitId) {
		case unitFanL: switch (parentSlice->sliceId) {
			case slice0: selLine=3; break;
			case slice1: selLine=2; break;
			case slice2: selLine=1; break;
			case slice3: selLine=0; break;
			default: error ("FAN invalid slice"); break;
		} selCol=0; break;
		case unitFanR: switch (parentSlice->sliceId) {
			case slice0: selLine=1; break;
			case slice1: selLine=0; break;
			case slice2: selLine=3; break;
			case slice3: selLine=2; break;
			default: error ("FAN invalid slice"); break;
		} selCol=1; break;
		default: error ("FAN invalid unitId"); break;
	}
	unsigned char cfgTile = endian(parentSlice->parentTile->parentChip->cfgBuf[parentSlice->parentTile->tileRowId][parentSlice->parentTile->tileColId][selRow][selCol][selLine]);
	switch (unitId) {
		case unitFanL: switch (parentSlice->sliceId) {
			case slice0: cfgTile = (cfgTile & 0b00111000) + (m_state.pmos & 0b00000111); break;
			case slice1: cfgTile = (cfgTile & 0b00111000) + (m_state.pmos & 0b00000111); break;
			case slice2: cfgTile = (cfgTile & 0b00111000) + (m_state.pmos & 0b00000111); break;
			case slice3: cfgTile = (cfgTile & 0b00111000) + (m_state.pmos & 0b00000111); break;
			default: error ("FAN invalid slice"); break;
		} break;
		case unitFanR: switch (parentSlice->sliceId) {
			case slice0: cfgTile = (cfgTile & 0b00000111) + ((m_state.pmos<<3) & 0b00111000); break;
			case slice1: cfgTile = (cfgTile & 0b00000111) + ((m_state.pmos<<3) & 0b00111000); break;
			case slice2: cfgTile = (cfgTile & 0b00111000) + (m_state.pmos & 0b00000111); break;
			case slice3: cfgTile = (cfgTile & 0b00111000) + (m_state.pmos & 0b00000111); break;
			default: error ("FAN invalid slice"); break;
		} break;
		default: error ("FAN invalid unitId"); break;
	}

	Vector vec = Vector (
		*this,
		selRow,
		selCol,
		selLine,
		endian (cfgTile)
	);

	parentSlice->parentTile->parentChip->cacheVec (
		vec
	);
}
