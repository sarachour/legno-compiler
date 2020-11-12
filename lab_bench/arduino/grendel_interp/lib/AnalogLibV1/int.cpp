#include "AnalogLib.h"
#include <float.h>
#include "calib_util.h"
#include "fu.h"
#include "assert.h"

float Fabric::Chip::Tile::Slice::Integrator::computeInitCond(integ_state_t& state){
  float sign = state.inv ? -1.0 : 1.0;
  float rng = util::range_to_coeff(state.range[out0Id])*2.0;
  float ic = (state.ic_code-128.0)/128.0;
  return rng*sign*ic;
}

float Fabric::Chip::Tile::Slice::Integrator::computeOutput(integ_state_t& state,float val){
  float sign = state.inv ? -1.0 : 1.0;
  float rng = util::range_to_coeff(state.range[out0Id])
    /util::range_to_coeff(state.range[in0Id]);
  return rng*sign*val;
}


float Fabric::Chip::Tile::Slice::Integrator::computeTimeConstant(integ_state_t& state){
  float rng = util::range_to_coeff(state.range[out0Id])
    /util::range_to_coeff(state.range[in0Id]);
  const float TIME_CONSTANT = NOMINAL_TIME_CONSTANT;
  return TIME_CONSTANT*rng;
}



void Fabric::Chip::Tile::Slice::Integrator::update(integ_state_t state){
  this->m_state = state;
  updateFu();
}
void Fabric::Chip::Tile::Slice::Integrator::setEnable (
	bool enable
) {
	this->m_state.enable = enable;
	setParam0 ();
	setParam1 ();
	setParam3 ();
	setParam4 ();
}

void Fabric::Chip::Tile::Slice::Integrator::setInv (
                                                    bool inverse // whether output is negated
                                                    )
{
	this->m_state.inv = inverse;
	setEnable (
		this->m_state.enable
	);
}

void Fabric::Chip::Tile::Slice::Integrator::setRange (ifc port,
                                                      range_t range) {
	/*check*/
  if(!(port == out0Id || port == in0Id)){
    error("cannot set range. invalid port");
  }
  this->m_state.range[port] = range;
	setEnable (this->m_state.enable);
}


void Fabric::Chip::Tile::Slice::Integrator::setInitialCode (
	unsigned char initialCode // fixed point representation of initial condition
) {
  this->m_state.ic_code = initialCode;
	setParam2 ();
}

void Fabric::Chip::Tile::Slice::Integrator::setInitial(float initial)
{
  if(-1.0000001 < initial && initial < 1.000001){
    setInitialCode(min(round(initial*128.0)+128.0,255));
  }
  else{
    error("integ.setInitial: only accepts constant values must be between -1 and 1");
  }
}


void Fabric::Chip::Tile::Slice::Integrator::setException (
	bool exception // turn on overflow detection
	// turning false overflow detection saves power if it is known to be unnecessary
) {
	this->m_state.exception = exception;
	setParam1 ();
}

bool Fabric::Chip::Tile::Slice::Integrator::getException () const {
	unsigned char exceptionVector;
	parentSlice->parentTile->readExp ( exceptionVector );
	// bits 0-3: Integrator overflow
	SerialUSB.print (exceptionVector);
	SerialUSB.print (" ");
	return bitRead (exceptionVector, parentSlice->sliceId);
}
void Fabric::Chip::Tile::Slice::Integrator::defaults (){
  this->m_state.pmos = 5;
  this->m_state.nmos = 0;
  this->m_state.ic_code = 128;
  this->m_state.inv = false;
  this->m_state.range[in0Id] = RANGE_MED;
  this->m_state.range[in1Id] = RANGE_UNKNOWN;
  this->m_state.range[out0Id] = RANGE_MED;
  this->m_state.cal_enable[in0Id] = false;
  this->m_state.cal_enable[in1Id] = false;
  this->m_state.cal_enable[out0Id] = false;
  this->m_state.port_cal[in0Id] = 31;
  this->m_state.port_cal[in1Id] = 0;
  this->m_state.port_cal[out0Id] = 31;
  this->m_state.exception = false;
  this->m_state.gain_cal = 32;
	setAnaIrefNmos();
	setAnaIrefPmos();
}

Fabric::Chip::Tile::Slice::Integrator::Integrator (
	Chip::Tile::Slice * parentSlice
) :
	FunctionUnit(parentSlice, unitInt)
{
	in0 = new Interface(this, in0Id);
	tally_dyn_mem <Interface> ("IntegratorIn");
	out0 = new Interface(this, out0Id);
	tally_dyn_mem <Interface> ("IntegratorOut");
  defaults();
}

/*Set enable, invert, range*/
void Fabric::Chip::Tile::Slice::Integrator::setParam0 () const {
	intRange intRange;
  bool out0_loRange = (this->m_state.range[out0Id] == RANGE_LOW);
  bool out0_hiRange = (this->m_state.range[out0Id] == RANGE_HIGH);
  bool in0_loRange = (this->m_state.range[in0Id] == RANGE_LOW);
  bool in0_hiRange = (this->m_state.range[in0Id] == RANGE_HIGH);

	if (out0_loRange) {
		if (in0_loRange) {
			intRange = mGainLRng;
		} else if (in0_hiRange) {
			error ("cannot set integrator output loRange when input hiRange");
		} else {
			intRange = lGainLRng;
		}
	} else if (out0_hiRange) {
		if (in0_loRange) {
			error ("cannot set integrator output hiRange when input loRange");
		} else if (in0_hiRange) {
			intRange = mGainHRng;
		} else {
			intRange = hGainHRng;
		}
	} else {
		if (in0_loRange) {
			intRange = hGainMRng;
		} else if (in0_hiRange) {
			intRange = lGainMRng;
		} else {
			intRange = mGainMRng;
		}
	}

	unsigned char cfgTile = 0;
	cfgTile += this->m_state.enable ? 1<<7 : 0;
	cfgTile += (this->m_state.inv) ? 1<<6 : 0;
	cfgTile += intRange<<3;
	setParamHelper (0, cfgTile);
}

/*Set calIc, overflow enable*/
void Fabric::Chip::Tile::Slice::Integrator::setParam1 () const {
	unsigned char cfgCalIc = this->m_state.gain_cal;
	if (cfgCalIc<0||63<cfgCalIc) error ("cfgCalIc out of bounds");
	unsigned char cfgTile = 0;
	cfgTile += cfgCalIc<<2;
	cfgTile += (this->m_state.exception) ? 1<<1 : 0;
	setParamHelper (1, cfgTile);
}

/*Set initial condition*/
void Fabric::Chip::Tile::Slice::Integrator::setParam2 () const {
	setParamHelper (2, this->m_state.ic_code);
}

/*Set calOutOs, calOutEn*/
void Fabric::Chip::Tile::Slice::Integrator::setParam3 () const {
	unsigned char calOutOs = this->m_state.port_cal[out0Id];
	if (calOutOs<0||63<calOutOs) error ("calOutOs out of bounds");
	unsigned char cfgTile = 0;
	cfgTile += calOutOs<<2;
	cfgTile += (this->m_state.cal_enable[out0Id]) ? 1<<1 : 0;
	setParamHelper (3, cfgTile);
}

/*Set calInOs, calInEn*/
void Fabric::Chip::Tile::Slice::Integrator::setParam4 () const {
	unsigned char calInOs = this->m_state.port_cal[in0Id];
	if (calInOs<0||63<calInOs){
    sprintf(FMTBUF, "calInOs out of bounds <%d>", calInOs);
    error (FMTBUF);
  }
	unsigned char cfgTile = 0;
	cfgTile += calInOs<<2;
	cfgTile += (this->m_state.cal_enable[in0Id]) ? 1<<1 : 0;
	setParamHelper (4, cfgTile);
}

/*Helper function*/
void Fabric::Chip::Tile::Slice::Integrator::setParamHelper (
	unsigned char selLine,
	unsigned char cfgTile
) const {
	if (selLine<0||4<selLine) error ("selLine out of bounds");

	/*DETERMINE SEL_ROW*/
	unsigned char selRow;
	switch (parentSlice->sliceId) {
		case slice0: selRow = 2; break;
		case slice1: selRow = 3; break;
		case slice2: selRow = 4; break;
		case slice3: selRow = 5; break;
		default: error ("invalid slice. Only slices 0 through 3 have INTs"); break;
	}

	Vector vec = Vector (
		*this,
		selRow,
		2,
		selLine,
		endian (cfgTile)
	);

	parentSlice->parentTile->parentChip->cacheVec (
		vec
	);
}


void Fabric::Chip::Tile::Slice::Integrator::setAnaIrefNmos () const {
	unsigned char selRow=0;
	unsigned char selCol=2;
	unsigned char selLine;
  util::test_iref(this->m_state.nmos);
	switch (parentSlice->sliceId) {
		case slice0: selLine=1; break;
		case slice1: selLine=2; break;
		case slice2: selLine=0; break;
		case slice3: selLine=3; break;
		default: error ("INT invalid slice"); break;
	}
	unsigned char cfgTile = endian(parentSlice->parentTile->parentChip->cfgBuf[parentSlice->parentTile->tileRowId][parentSlice->parentTile->tileColId][selRow][selCol][selLine]);
	cfgTile = (cfgTile & 0b00000111) + ((this->m_state.nmos<<3) & 0b00111000);

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

void Fabric::Chip::Tile::Slice::Integrator::setAnaIrefPmos () const {

	unsigned char selRow=0;
	unsigned char selCol;
	unsigned char selLine;
  util::test_iref(this->m_state.pmos);
	switch (parentSlice->sliceId) {
		case slice0: selCol=3; selLine=4; break;
		case slice1: selCol=3; selLine=5; break;
		case slice2: selCol=4; selLine=3; break;
		case slice3: selCol=4; selLine=4; break;
		default: error ("INT invalid slice"); break;
	}
	unsigned char cfgTile = endian(parentSlice->parentTile->parentChip->cfgBuf[parentSlice->parentTile->tileRowId][parentSlice->parentTile->tileColId][selRow][selCol][selLine]);
	switch (parentSlice->sliceId) {
		case slice0: cfgTile = (cfgTile & 0b00111000) + (this->m_state.pmos & 0b00000111); break;
		case slice1: cfgTile = (cfgTile & 0b00000111) + ((this->m_state.pmos<<3) & 0b00111000); break;
		case slice2: cfgTile = (cfgTile & 0b00111000) + (this->m_state.pmos & 0b00000111); break;
		case slice3: cfgTile = (cfgTile & 0b00111000) + (this->m_state.pmos & 0b00000111); break;
		default: error ("INT invalid slice"); break;
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
