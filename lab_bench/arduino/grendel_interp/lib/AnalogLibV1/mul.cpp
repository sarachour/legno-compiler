#include "AnalogLib.h"
#include "fu.h"
#include "mul.h"
#include "calib_util.h"
#include <float.h>

void Fabric::Chip::Tile::Slice::Multiplier::computeInterval(mult_state_t& state,
                                                        port_type_t port, float& min, float& max){
  float ampl = 2.0;
  switch(port){
  case in0Id:
    ampl = state.range[in0Id] == RANGE_HIGH ? 20.0 : 2.0;
    break;
  case in1Id:
    ampl = state.range[in1Id] == RANGE_HIGH ? 20.0 : 2.0;
    break;
  case out0Id:
    ampl = state.range[out0Id] == RANGE_HIGH ? 20.0 : 2.0;
    break;
  default:
    error("multiplier was supplied unknown port");
  }
  min = -ampl;
  max = ampl;
}

void Fabric::Chip::Tile::Slice::Multiplier::update(mult_state_t codes){
  this->m_state = codes;
  updateFu();
}


float Fabric::Chip::Tile::Slice::Multiplier::computeOutput(mult_state_t& codes,
                                                           float in0,
                                                           float in1){
  float gain = (codes.gain_code-128.0)/128.0;
  float rng = util::range_to_coeff(codes.range[out0Id]);
  rng *= 1.0/util::range_to_coeff(codes.range[in0Id]);

  if(codes.vga){
    return gain*rng*in0;
  }
  else{
    rng *= 1.0/util::range_to_coeff(codes.range[in1Id]);
    return 0.5*rng*in0*in1;
  }
}


void Fabric::Chip::Tile::Slice::Multiplier::setEnable (
	bool enable
) {
	this->m_state.enable = enable;
	setParam0 ();
	/*establish calibration codes*/
	setParam1 ();
	setParam3 ();
	setParam4 ();
	setParam5 ();
}

void Fabric::Chip::Tile::Slice::Multiplier::setVga (
	bool vga // constant coefficient multiplier mode
) {
	this->m_state.vga = vga;
	setParam1 ();
}

void Fabric::Chip::Tile::Slice::Multiplier::setGainCode (
	unsigned char gainCode // fixed point representation of desired gain
) {
	// Serial.println("setGainCode");
	// Serial.println(gainCode);
	setVga (true);
	this->m_state.gain_code = gainCode;
	setParam2 ();
}

void Fabric::Chip::Tile::Slice::Multiplier::setGain(float gain){
  if(-1.0000001 < gain && gain < 1.0000001){
    setGainCode(min(255,round(gain*128.0)+128.0));
  }
  else{
    sprintf(FMTBUF,"mult.setGain: constant values must be between -1 and 1, gain=%f",gain);
    error(FMTBUF);
  }
}



void Fabric::Chip::Tile::Slice::Multiplier::setRange (ifc port,
                                                      range_t range) {
  if(!(port == in0Id || port == in1Id || port == out0Id)){
    error("unsupported range");
  }
  this->m_state.range[port] = range;
	setParam0 ();
	setParam3 ();
	setParam4 ();
	setParam5 ();
}

void Fabric::Chip::Tile::Slice::Multiplier::defaults () {
  this->m_state.pmos = 3;
  this->m_state.nmos = 0;
  this->m_state.vga = false;
  this->m_state.gain_code = 128;
  this->m_state.gain_cal = 0;
  this->m_state.range[in0Id] = RANGE_MED;
  this->m_state.range[in1Id] = RANGE_MED;
  this->m_state.range[out0Id] = RANGE_MED;
  this->m_state.port_cal[in0Id] = 31;
  this->m_state.port_cal[in1Id] = 31;
  this->m_state.port_cal[out0Id] = 31;
  this->m_state.enable = false;
  setAnaIrefNmos();
	setAnaIrefPmos();
}


Fabric::Chip::Tile::Slice::Multiplier::Multiplier (
	Slice * parentSlice,
	unit unitId
) :
	FunctionUnit(parentSlice, unitId)
{
	out0 = new Interface(this, out0Id);
	tally_dyn_mem <Interface> ("MultiplierInterface");
	in0 = new Interface (this, in0Id);
	tally_dyn_mem <Interface> ("MultiplierInterface");
	in1 = new Interface (this, in1Id);
	tally_dyn_mem <Interface> ("MultiplierInterface");
  defaults();
}

mulRange range_to_mulRange(range_t rng){
  switch(rng){
  case RANGE_HIGH: return mulHi;
  case RANGE_LOW: return mulLo;
  case RANGE_MED: return mulMid;
  default: error("unknown range");
  }
  return mulMid;
}
/*Set enable, input 1 range, input 2 range, output range*/
void Fabric::Chip::Tile::Slice::Multiplier::setParam0 () const {
	unsigned char cfgTile = 0;
	cfgTile += this->m_state.enable ? 1<<7 : 0;
	cfgTile += (range_to_mulRange(this->m_state.range[in0Id]))<<4;
	cfgTile += (range_to_mulRange(this->m_state.range[in1Id]))<<2;
	cfgTile += (range_to_mulRange(this->m_state.range[out0Id]))<<0;
	setParamHelper (0, cfgTile);
}

/*Set calDac, enable variable gain amplifer mode*/
void Fabric::Chip::Tile::Slice::Multiplier::setParam1 () const {
  unsigned char negGainCalCode = this->m_state.gain_cal;
	if (negGainCalCode<0||63<negGainCalCode) error ("midNegGainCode out of bounds");
	unsigned char cfgTile = 0;
	cfgTile += negGainCalCode<<2;
	cfgTile += this->m_state.vga ? 1<<1 : 0;
	setParamHelper (1, cfgTile);
}

/*Set gain if VGA mode*/
void Fabric::Chip::Tile::Slice::Multiplier::setParam2 () const {
  unsigned char gainCode = this->m_state.gain_code;
	if (gainCode<0||255<gainCode) error ("gain out of bounds");
	setParamHelper (2, gainCode);
}

/*Set calOutOs*/
void Fabric::Chip::Tile::Slice::Multiplier::setParam3 () const {
  unsigned char calOutOs = this->m_state.port_cal[out0Id];
	if (calOutOs<0||63<calOutOs) error ("calOutOs out of bounds");
	unsigned char cfgTile = calOutOs<<2;
	setParamHelper (3, cfgTile);
}

/*Set calInOs1*/
void Fabric::Chip::Tile::Slice::Multiplier::setParam4 () const {
  unsigned char calInOs1 = this->m_state.port_cal[in0Id];
	if (calInOs1<0||63<calInOs1) error ("calInOs1 out of bounds");
	unsigned char cfgTile = calInOs1<<2;
	setParamHelper (4, cfgTile);
}

/*Set calInOs2*/
void Fabric::Chip::Tile::Slice::Multiplier::setParam5 () const {
  unsigned char calInOs2 = this->m_state.port_cal[in1Id];
	if (calInOs2<0||63<calInOs2) error ("calInOs2 out of bounds");
	unsigned char cfgTile = calInOs2<<2;
	setParamHelper (5, cfgTile);
}

void Fabric::Chip::Tile::Slice::Multiplier::setParamHelper (
	unsigned char selLine,
	unsigned char cfgTile
) const {
	if (selLine<0||5<selLine) error ("selLine out of bounds");

	/*DETERMINE SEL_ROW*/
	unsigned char selRow;
	switch (parentSlice->sliceId) {
		case slice0: selRow = 2; break;
		case slice1: selRow = 3; break;
		case slice2: selRow = 4; break;
		case slice3: selRow = 5; break;
		default: error ("invalid slice. Only slices 0 through 3 have MULs"); break;
	}

	/*DETERMINE SEL_COL*/
	unsigned char selCol;
	switch (unitId) {
		case unitMulL: selCol = 3; break;
		case unitMulR: selCol = 4; break;
		default: error ("invalid unit. Only unitMulL and unitMulR are MULs"); break;
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



void Fabric::Chip::Tile::Slice::Multiplier::setAnaIrefNmos () const {
	unsigned char selRow;
	unsigned char selCol;
	unsigned char selLine;
  util::test_iref(this->m_state.nmos);
	switch (unitId) {
		case unitMulL: switch (parentSlice->sliceId) {
			case slice0: selRow=1; selCol=2; selLine=1; break;
			case slice1: selRow=0; selCol=3; selLine=0; break;
			case slice2: selRow=1; selCol=2; selLine=0; break;
			case slice3: selRow=0; selCol=3; selLine=1; break;
			default: error ("MUL invalid slice"); break;
		} break;
		case unitMulR: switch (parentSlice->sliceId) {
			case slice0: selRow=1; selCol=2; selLine=3; break;
			case slice1: selRow=0; selCol=3; selLine=2; break;
			case slice2: selRow=1; selCol=2; selLine=2; break;
			case slice3: selRow=0; selCol=3; selLine=3; break;
			default: error ("MUL invalid slice"); break;
		} break;
		default: error ("MUL invalid unitId"); break;
	}
	unsigned char cfgTile = endian(parentSlice->parentTile->parentChip->cfgBuf[parentSlice->parentTile->tileRowId][parentSlice->parentTile->tileColId][selRow][selCol][selLine]);
	switch (unitId) {
		case unitMulL: switch (parentSlice->sliceId) {
			case slice0: cfgTile = (cfgTile & 0b00000111) + ((this->m_state.nmos<<3) & 0b00111000); break;
			case slice1: cfgTile = (cfgTile & 0b00111000) + (this->m_state.nmos & 0b00000111); break;
			case slice2: cfgTile = (cfgTile & 0b00000111) + ((this->m_state.nmos<<3) & 0b00111000); break;
			case slice3: cfgTile = (cfgTile & 0b00111000) + (this->m_state.nmos & 0b00000111); break;
			default: error ("MUL invalid slice"); break;
		} break;
		case unitMulR: switch (parentSlice->sliceId) {
			case slice0: cfgTile = (cfgTile & 0b00111000) + (this->m_state.nmos & 0b00000111); break;
			case slice1: cfgTile = (cfgTile & 0b00111000) + (this->m_state.nmos & 0b00000111); break;
			case slice2: cfgTile = (cfgTile & 0b00111000) + (this->m_state.nmos & 0b00000111); break;
			case slice3: cfgTile = (cfgTile & 0b00111000) + (this->m_state.nmos & 0b00000111); break;
			default: error ("MUL invalid slice"); break;
		} break;
		default: error ("MUL invalid unitId"); break;
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

void Fabric::Chip::Tile::Slice::Multiplier::setAnaIrefPmos () const {

	unsigned char setting=7-this->m_state.pmos; // because pmos setting has opposite effect on gain
	unsigned char selRow=0;
	unsigned char selCol=4;
	unsigned char selLine;
  util::test_iref(this->m_state.pmos);
	switch (unitId) {
		case unitMulL: switch (parentSlice->sliceId) {
			case slice0: selLine=2; break;
			case slice1: selLine=5; break;
			case slice2: selLine=1; break;
			case slice3: selLine=0; break;
			default: error ("MUL invalid slice"); break;
		} break;
		case unitMulR: switch (parentSlice->sliceId) {
			case slice0: selLine=0; break;
			case slice1: selLine=1; break;
			case slice2: selLine=2; break;
			case slice3: selLine=3; break;
			default: error ("MUL invalid slice"); break;
		} break;
		default: error ("MUL invalid unitId"); break;
	}
	unsigned char cfgTile = endian(parentSlice->parentTile->parentChip->cfgBuf[parentSlice->parentTile->tileRowId][parentSlice->parentTile->tileColId][selRow][selCol][selLine]);
	switch (unitId) {
		case unitMulL: switch (parentSlice->sliceId) {
			case slice0: cfgTile = (cfgTile & 0b00111000) + (setting & 0b00000111); break;
			case slice1: cfgTile = (cfgTile & 0b00111000) + (setting & 0b00000111); break;
			case slice2: cfgTile = (cfgTile & 0b00111000) + (setting & 0b00000111); break;
			case slice3: cfgTile = (cfgTile & 0b00000111) + ((setting<<3) & 0b00111000); break;
			default: error ("MUL invalid slice"); break;
		} break;
		case unitMulR: switch (parentSlice->sliceId) {
			case slice0: cfgTile = (cfgTile & 0b00111000) + (setting & 0b00000111); break;
			case slice1: cfgTile = (cfgTile & 0b00000111) + ((setting<<3) & 0b00111000); break;
			case slice2: cfgTile = (cfgTile & 0b00000111) + ((setting<<3) & 0b00111000); break;
			case slice3: cfgTile = (cfgTile & 0b00000111) + ((setting<<3) & 0b00111000); break;
			default: error ("MUL invalid slice"); break;
		} break;
		default: error ("MUL invalid unitId"); break;
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
