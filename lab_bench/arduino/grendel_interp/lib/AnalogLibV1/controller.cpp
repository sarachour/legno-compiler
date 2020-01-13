#include "AnalogLib.h"

/*empty instruction vector*/
// send empty instruction vector to controller address, 0101,1000,0000,0000
const bool noOp[] = {
	false, true, false, true,
	true, false, false, false,
	false, false, false, false,
	false, false, false, false,
	false, false, false, false,
	false, false, false, false
};

/*Configuration start*/
void Fabric::cfgStart () {
	cfgState = true;
	stateMachine();
}

/*Configuration commit*/
void Fabric::cfgCommit () {
  print_debug("start configure (cfgStart)");
	cfgStart();
  print_debug("writing vects to chip 0");
	chips[0].writeVecs();
  print_debug("writing vects to chip 1");
	chips[1].writeVecs();
  print_debug("stop configure (cfgStop)");
	cfgStop();
  print_debug("done");
}

/*Configuration stop*/
void Fabric::cfgStop () {
	cfgState = false;
	stateMachine();
}

/*Start calculation execution*/
void Fabric::execStart () {
	execState = true;
	stateMachine();
}

/*Stop calculation execution*/
void Fabric::execStop () {
	execState = false;
	stateMachine();
}

void Fabric::stateMachine () const {
	unsigned char cfgTile = 0b00000000;
	cfgTile += cfgState ? 1<<7 : 0;
	cfgTile += execState ? 1<<6 : 0;
	cfgTile += dataState ? 1<<5 : 0;
	cfgTile += expState ? 1<<4 : 0;
	controllerHelperFabric (1, cfgTile);
}

/*Set timeout value*/
void Fabric::setTimeout (unsigned int timeout) const {
  // this determines how long to hold the initial conditions
  // it needs to be surrounded with a cfg start and config-stop
	Serial.print("timeout: ");
	Serial.println(timeout);
	if (timeout<0||4294967295<timeout) error ("timeout out of bounds");
	unsigned int timeoutReg0 = (timeout & 0xff000000) >> 24;
	controllerHelperFabric (3, timeoutReg0);
	unsigned int timeoutReg1 = (timeout & 0x00ff0000) >> 16;
	controllerHelperFabric (4, timeoutReg1);
	unsigned int timeoutReg2 = (timeout & 0x0000ff00) >> 8;
	controllerHelperFabric (5, timeoutReg2);
	unsigned int timeoutReg3 = (timeout & 0x000000ff) >> 0;
	controllerHelperFabric (6, timeoutReg3);
}

void Fabric::controllerHelperFabric (unsigned char selLine,
                                     unsigned char cfgTile) const {
	if (selLine<0||6<selLine) error ("selLine out of bounds");
	if (cfgTile<0||255<cfgTile) error ("cfgTile out of bounds");

  sprintf(FMTBUF,"CTRLFAB %d %d", selLine,cfgTile);
  print_debug(FMTBUF);
	/*if arduino form, check that sram vector fields are within bounds*/
	// should only be used by controller and lut param writes
	digitalWriteDirect (chips[0].tiles[0].spiSSPin, LOW);
	digitalWriteDirect (chips[0].tiles[1].spiSSPin, LOW);
	digitalWriteDirect (chips[0].tiles[2].spiSSPin, LOW);
	digitalWriteDirect (chips[0].tiles[3].spiSSPin, LOW);
	digitalWriteDirect (chips[1].tiles[0].spiSSPin, LOW);
	digitalWriteDirect (chips[1].tiles[1].spiSSPin, LOW);
	digitalWriteDirect (chips[1].tiles[2].spiSSPin, LOW);
	digitalWriteDirect (chips[1].tiles[3].spiSSPin, LOW);
	spiDrive ( 8, 0, selLine, cfgTile );
	// this is necessary
	spiDrive (noOp, 9);
	digitalWriteDirect (chips[0].tiles[0].spiSSPin, HIGH);
	digitalWriteDirect (chips[0].tiles[1].spiSSPin, HIGH);
	digitalWriteDirect (chips[0].tiles[2].spiSSPin, HIGH);
	digitalWriteDirect (chips[0].tiles[3].spiSSPin, HIGH);
	digitalWriteDirect (chips[1].tiles[0].spiSSPin, HIGH);
	digitalWriteDirect (chips[1].tiles[1].spiSSPin, HIGH);
	digitalWriteDirect (chips[1].tiles[2].spiSSPin, HIGH);
	digitalWriteDirect (chips[1].tiles[3].spiSSPin, HIGH);
}

/*Internal function*/
void Fabric::Chip::controllerHelperChip (unsigned char selLine, unsigned char cfgTile) const {
	if (selLine<0||6<selLine) error ("selLine out of bounds");
	if (cfgTile<0||255<cfgTile) error ("cfgTile out of bounds");
  sprintf(FMTBUF,"CTRLCHIP %d %d", selLine,cfgTile);
  print_debug(FMTBUF);
	/*if arduino form, check that sram vector fields are within bounds*/
	// should only be used by controller and lut param writes
	spiDriveChip ( 8, 0, selLine, cfgTile );
	// this is necessary
	spiDriveChip (noOp);
}


/*Internal function*/
void Fabric::Chip::Tile::controllerHelperTile (
                                               unsigned char selLine,
                                               unsigned char cfgTile
                                               ) const {
	if (selLine<7||11<selLine) error ("selLine out of bounds");
	if (cfgTile<0||255<cfgTile) error ("cfgTile out of bounds");
  sprintf(FMTBUF,"CTRLTILE %d %d", selLine,cfgTile);
  print_debug(FMTBUF);
	/*if arduino form, check that sram vector fields are within bounds*/
	// should only be used by controller and lut param writes
	// Serial.print("vec.tileRowId = "); Serial.println(vec.tileRowId);
	// Serial.print("vec.tileColId = "); Serial.println(vec.tileColId);
	// Serial.print("vec.selRow = "); Serial.println(vec.selRow);
	// Serial.print("vec.selCol = "); Serial.println(vec.selCol);
	// Serial.print("vec.cfgTile = "); Serial.println(vec.cfgTile);
	spiDriveTile ( 8, 0, selLine, cfgTile );
	spiDriveTile (noOp);
}
