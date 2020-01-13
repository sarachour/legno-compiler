#include "AnalogLib.h"

Fabric::Chip::Tile::Tile (
	Chip * parentChip,
	tileRow tileRowId,
	tileCol tileColId,
	unsigned char spiSSPin,
	unsigned char spiMisoPin,
	unsigned char ardAnaDiffChanBase
) :
	parentChip (parentChip),
	tileRowId (tileRowId),
	tileColId (tileColId),
	spiSSPin (spiSSPin),
	spiMisoPin (spiMisoPin)
{
  	pinMode(spiSSPin, OUTPUT);
	digitalWrite (spiSSPin, HIGH);
	pinMode(spiMisoPin, INPUT);

	slices = new Slice[4] {
		Slice (this, slice0, 12), // dummy ardAnaDiffChan
		Slice (this, slice1, 12),
		Slice (this, slice2, ardAnaDiffChanBase+2), // 6 and 2
		Slice (this, slice3, ardAnaDiffChanBase+0)  // 4 and 0
	};
}

Fabric::Chip::Tile::~Tile() { delete[] slices; };

void Fabric::Chip::Tile::defaults() {
	slices[0].defaults();
	slices[1].defaults();
	slices[2].defaults();
	slices[3].defaults();
	return true;
};

void Fabric::Chip::Tile::spiDriveTile (
	unsigned char selRow,
	unsigned char selCol,
	unsigned char selLine,
	unsigned char cfgTile
) const {
	digitalWriteDirect (spiSSPin, LOW);
	spiDrive ( selRow, selCol, selLine, cfgTile );
	digitalWriteDirect (spiSSPin, HIGH);
}

int Fabric::Chip::Tile::spiDriveTile ( const bool * vector ) const {
	digitalWriteDirect (spiSSPin, LOW);
	// Serial.print("spiMisoPin = "); Serial.println(spiMisoPin);
	unsigned int result = spiDrive ( vector, spiMisoPin );
	// Serial.print("result = "); Serial.println(result);
	digitalWriteDirect (spiSSPin, HIGH);
	return result;
}
