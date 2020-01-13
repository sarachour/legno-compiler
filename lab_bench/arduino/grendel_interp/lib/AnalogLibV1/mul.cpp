#include "AnalogLib.h"
#include "fu.h"
#include "mul.h"
#include "calib_util.h"
#include <float.h>

void Fabric::Chip::Tile::Slice::Multiplier::update(mult_code_t codes){
  m_codes = codes;
  updateFu();
}


float Fabric::Chip::Tile::Slice::Multiplier::computeOutput(mult_code_t& m_codes,
                                                           float in0,
                                                           float in1){
  float gain = (m_codes.gain_code-128.0)/128.0;
  float rng = util::range_to_coeff(m_codes.range[out0Id]);
  rng *= 1.0/util::range_to_coeff(m_codes.range[in0Id]);

  if(m_codes.vga){
    return gain*rng*in0;
  }
  else{
    rng *= 1.0/util::range_to_coeff(m_codes.range[in1Id]);
    return rng*in0*in1;
  }
}


void Fabric::Chip::Tile::Slice::Multiplier::setEnable (
	bool enable
) {
	m_codes.enable = enable;
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
	m_codes.vga = vga;
	setParam1 ();
}

void Fabric::Chip::Tile::Slice::Multiplier::setGainCode (
	unsigned char gainCode // fixed point representation of desired gain
) {
	// Serial.println("setGainCode");
	// Serial.println(gainCode);
	setVga (true);
	m_codes.gain_code = gainCode;
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
  m_codes.range[port] = range;
	setParam0 ();
	setParam3 ();
	setParam4 ();
	setParam5 ();
}

void Fabric::Chip::Tile::Slice::Multiplier::defaults () {
  m_codes.pmos = 3;
  m_codes.nmos = 0;
  m_codes.vga = false;
  m_codes.gain_code = 128;
  m_codes.gain_cal = 0;
  m_codes.range[in0Id] = RANGE_MED;
  m_codes.range[in1Id] = RANGE_MED;
  m_codes.range[out0Id] = RANGE_MED;
  m_codes.port_cal[in0Id] = 31;
  m_codes.port_cal[in1Id] = 31;
  m_codes.port_cal[out0Id] = 31;
  m_codes.enable = false;
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
	cfgTile += m_codes.enable ? 1<<7 : 0;
	cfgTile += (range_to_mulRange(m_codes.range[in0Id]))<<4;
	cfgTile += (range_to_mulRange(m_codes.range[in1Id]))<<2;
	cfgTile += (range_to_mulRange(m_codes.range[out0Id]))<<0;
	setParamHelper (0, cfgTile);
}

/*Set calDac, enable variable gain amplifer mode*/
void Fabric::Chip::Tile::Slice::Multiplier::setParam1 () const {
  unsigned char negGainCalCode = m_codes.gain_cal;
	if (negGainCalCode<0||63<negGainCalCode) error ("midNegGainCode out of bounds");
	unsigned char cfgTile = 0;
	cfgTile += negGainCalCode<<2;
	cfgTile += m_codes.vga ? 1<<1 : 0;
	setParamHelper (1, cfgTile);
}

/*Set gain if VGA mode*/
void Fabric::Chip::Tile::Slice::Multiplier::setParam2 () const {
  unsigned char gainCode = m_codes.gain_code;
	if (gainCode<0||255<gainCode) error ("gain out of bounds");
	setParamHelper (2, gainCode);
}

/*Set calOutOs*/
void Fabric::Chip::Tile::Slice::Multiplier::setParam3 () const {
  unsigned char calOutOs = m_codes.port_cal[out0Id];
	if (calOutOs<0||63<calOutOs) error ("calOutOs out of bounds");
	unsigned char cfgTile = calOutOs<<2;
	setParamHelper (3, cfgTile);
}

/*Set calInOs1*/
void Fabric::Chip::Tile::Slice::Multiplier::setParam4 () const {
  unsigned char calInOs1 = m_codes.port_cal[in0Id];
	if (calInOs1<0||63<calInOs1) error ("calInOs1 out of bounds");
	unsigned char cfgTile = calInOs1<<2;
	setParamHelper (4, cfgTile);
}

/*Set calInOs2*/
void Fabric::Chip::Tile::Slice::Multiplier::setParam5 () const {
  unsigned char calInOs2 = m_codes.port_cal[in1Id];
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
  util::test_iref(m_codes.nmos);
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
			case slice0: cfgTile = (cfgTile & 0b00000111) + ((m_codes.nmos<<3) & 0b00111000); break;
			case slice1: cfgTile = (cfgTile & 0b00111000) + (m_codes.nmos & 0b00000111); break;
			case slice2: cfgTile = (cfgTile & 0b00000111) + ((m_codes.nmos<<3) & 0b00111000); break;
			case slice3: cfgTile = (cfgTile & 0b00111000) + (m_codes.nmos & 0b00000111); break;
			default: error ("MUL invalid slice"); break;
		} break;
		case unitMulR: switch (parentSlice->sliceId) {
			case slice0: cfgTile = (cfgTile & 0b00111000) + (m_codes.nmos & 0b00000111); break;
			case slice1: cfgTile = (cfgTile & 0b00111000) + (m_codes.nmos & 0b00000111); break;
			case slice2: cfgTile = (cfgTile & 0b00111000) + (m_codes.nmos & 0b00000111); break;
			case slice3: cfgTile = (cfgTile & 0b00111000) + (m_codes.nmos & 0b00000111); break;
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

	unsigned char setting=7-m_codes.pmos; // because pmos setting has opposite effect on gain
	unsigned char selRow=0;
	unsigned char selCol=4;
	unsigned char selLine;
  util::test_iref(m_codes.pmos);
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
