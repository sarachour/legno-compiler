#include "AnalogLib.h"

/*Set parallel digital data output on off*/
void Fabric::Chip::Tile::Slice::FunctionUnit::setParallelOut (
	bool onOff
) const {
  Fabric::Chip* chip = parentSlice->parentTile->parentChip;
	chip->parallelOutTileRow = parentSlice->parentTile->tileRowId;
	chip->parallelOutTileCol = parentSlice->parentTile->tileColId;
	switch (parentSlice->sliceId) {
		case slice0: chip->parallelOutSlice = slice0; break;
		case slice2: chip->parallelOutSlice = slice2; break;
		default: error ("setParallelOut invalid slice. Only even slices");
	}
	switch (unitId) {
		case unitAdc: chip->parallelOutUnit = unitAdc; break;
		case unitLut: chip->parallelOutUnit = unitLut; break;
		default: error ("invalid unit. Only adc, lut to parallel output");
	}
	chip->parallelOutState = onOff;
	chip->parallelHelper ();
}

/*Set parallel digital data input on off*/
void Fabric::Chip::Tile::setParallelIn (
                                        bool onOff
                                        ) const {
  Fabric::Chip* chip = parentChip;
	chip->parallelOutTileRow = tileRowId;
	chip->parallelOutTileCol = tileColId;
	chip->parallelInState = onOff;
	chip->parallelHelper ();
}


void Fabric::Chip::parallelHelper() const {
	// macro01 pin25=LOW tdRow:=pin25
	digitalWrite(tpSel0RowSelPin, parallelOutTileRow==tileRow1?HIGH:LOW);
	// macro01 pin24=HIGH tdCol:=pin24
	digitalWrite(tpSel1ColSelPin, parallelOutTileCol==tileCol1?HIGH:LOW);
	unsigned char cfgTile = 0b00000000;
	// Serial.print("parallelInState = "); Serial.println(parallelInState);
	cfgTile += parallelInState ? 1<<7 : 0;
	cfgTile += parallelOutState ? 1<<6 : 0;
	switch (parallelOutUnit) {
		case unitAdc:
			if (parallelOutSlice==slice0) {cfgTile += 0b00<<4;}
			else if (parallelOutSlice==slice2) {cfgTile += 0b01<<4;}
			else error ("setParallelIn invalid slice. Only even slices have ADCs");
		break;
		case unitLut:
			if (parallelOutSlice==slice0) {cfgTile += 0b10<<4;}
			else if (parallelOutSlice==slice2) {cfgTile += 0b11<<4;}
			else error ("setParallelIn invalid slice. Only even slices have LUTs");
		break;
		default: error ("invalid unit. Only adcL, adcR, lutL, lutR to parallel output"); break;
	}
	controllerHelperChip ( 2, cfgTile );
}

/*Read parallel digtal data*/
unsigned char Fabric::Chip::readParallel() const {
	digitalWrite(tpSelChipSelPin, HIGH);
	unsigned char readParallelData = 0;
#ifdef _DUE
	if (digitalReadDirect(tdo0Pin)==HIGH) readParallelData += bit(0);
	if (digitalReadDirect(tdo1Pin)==HIGH) readParallelData += bit(1);
	if (digitalReadDirect(tdo2Pin)==HIGH) readParallelData += bit(2);
	if (digitalReadDirect(tdo3Pin)==HIGH) readParallelData += bit(3);
	if (digitalReadDirect(tdo4Pin)==HIGH) readParallelData += bit(4);
	if (digitalReadDirect(tdo5Pin)==HIGH) readParallelData += bit(5);
	if (digitalReadDirect(tdo6Pin)==HIGH) readParallelData += bit(6);
	if (digitalReadDirect(tdo7Pin)==HIGH) readParallelData += bit(7);
#else
	if (digitalRead(tdo0Pin)==HIGH) readParallelData += bit(0);
	if (digitalRead(tdo1Pin)==HIGH) readParallelData += bit(1);
	if (digitalRead(tdo2Pin)==HIGH) readParallelData += bit(2);
	if (digitalRead(tdo3Pin)==HIGH) readParallelData += bit(3);
	if (digitalRead(tdo4Pin)==HIGH) readParallelData += bit(4);
	if (digitalRead(tdo5Pin)==HIGH) readParallelData += bit(5);
	if (digitalRead(tdo6Pin)==HIGH) readParallelData += bit(6);
	if (digitalRead(tdo7Pin)==HIGH) readParallelData += bit(7);
#endif
	digitalWrite(tpSelChipSelPin, LOW);
	return readParallelData;
}


/*Write parallel digital data*/
void Fabric::Chip::writeParallel(unsigned char data) const {
#ifdef _DUE
	digitalWriteDirect(tdi0Pin, bitRead(data, 0));
	digitalWriteDirect(tdi1Pin, bitRead(data, 1));
	digitalWriteDirect(tdi2Pin, bitRead(data, 2));
	digitalWriteDirect(tdi3Pin, bitRead(data, 3));
	digitalWriteDirect(tdi4Pin, bitRead(data, 4));
	digitalWriteDirect(tdi5Pin, bitRead(data, 5));
	digitalWriteDirect(tdi6Pin, bitRead(data, 6));
	digitalWriteDirect(tdi7Pin, bitRead(data, 7));
#else
	digitalWrite(tdi0Pin, bitRead(data, 0));
	digitalWrite(tdi1Pin, bitRead(data, 1));
	digitalWrite(tdi2Pin, bitRead(data, 2));
	digitalWrite(tdi3Pin, bitRead(data, 3));
	digitalWrite(tdi4Pin, bitRead(data, 4));
	digitalWrite(tdi5Pin, bitRead(data, 5));
	digitalWrite(tdi6Pin, bitRead(data, 6));
	digitalWrite(tdi7Pin, bitRead(data, 7));
#endif
	/*pulse the trigger*/
	digitalWrite(tdiClkPin, LOW);
	/*pulse the trigger*/
	digitalWrite(tdiClkPin, HIGH);
	/*pulse the trigger*/
	digitalWrite(tdiClkPin, LOW);
	return;
}
