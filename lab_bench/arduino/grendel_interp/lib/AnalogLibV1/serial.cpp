#include "AnalogLib.h"

/*Start serial digital data output*/
void Fabric::serialOutReq () {
	dataState = true;
	stateMachine();
}

/*Stop serial digital data output*/
void Fabric::serialOutStop () {
	dataState = false;
	stateMachine();
}

/*Read serial digital data and the done bit*/
void Fabric::Chip::Tile::readSerial (
	unsigned char & adcData0,
	unsigned char & adcData1,
	bool & done
) const {
	parentChip->parentFabric->serialOutReq();
	unsigned int misoBuffer = spiDriveTile ( noOp );
	adcData0 = (misoBuffer & 0x00ff00/*0b00000000_11111111_00000000*/) >> 8;
	adcData1 = (misoBuffer & 0xff0000/*0b11111111_00000000_00000000*/) >> 16;
	done =
		bitRead (misoBuffer, 4) == 0b1 &&
		bitRead (misoBuffer, 5) == 0b1 &&
		bitRead (misoBuffer, 6) == 0b1 &&
		bitRead (misoBuffer, 7) == 0b1;
	parentChip->parentFabric->serialOutStop();
	return;
}

/*Start exception output*/
void Fabric::expReq () {
	expState = true;
	stateMachine();
}

/*Read the exception bits*/
void Fabric::Chip::Tile::readExp (
	unsigned char & expVector
) const {
	parentChip->parentFabric->expReq();
	// bits 0-3: Integrator overflow
	// bits 4-5: L ADC exception
	// bits 6-7: R ADC exception
	// bits 5,7: ADC underflow
	// bits 4,6: ADC overflow
	unsigned int misoBuffer =  spiDriveTile ( noOp );
	expVector = (misoBuffer & 0x0000ff/*0b00000000_00000000_11111111*/) >> 0;
	parentChip->parentFabric->expStop();
	return;
}

/*Stop exception output*/
void Fabric::expStop () {
	expState = false;
	stateMachine();
}
