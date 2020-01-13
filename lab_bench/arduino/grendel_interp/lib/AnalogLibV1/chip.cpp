#include "AnalogLib.h"

Fabric::Chip::Chip (
	Fabric * parentFabric,
	chipRow chipRowId,
	chipCol chipColId,
	unsigned char tpSelChipSelPin,
	unsigned char tpSel0RowSelPin,
	unsigned char tpSel1ColSelPin,
	unsigned char spiSSPinBase,
	unsigned char spiMisoPinBase,
	unsigned char ardAnaDiffChanBase
) :
	parentFabric (parentFabric),
	chipRowId (chipRowId),
	chipColId (chipColId),
	tpSelChipSelPin (tpSelChipSelPin),
	tpSel0RowSelPin (tpSel0RowSelPin),
	tpSel1ColSelPin (tpSel1ColSelPin),
	spiSSPinBase (spiSSPinBase),
	spiMisoPinBase (spiMisoPinBase),
	ardAnaDiffChanBase (ardAnaDiffChanBase)
{

	pinMode(tpSelChipSelPin, OUTPUT);
	pinMode(tpSel0RowSelPin, OUTPUT);
	pinMode(tpSel1ColSelPin, OUTPUT);

	/*HCDC DIGITAL INPUT PINS*/
	pinMode(tdi0Pin, OUTPUT);
	pinMode(tdi1Pin, OUTPUT);
	pinMode(tdi2Pin, OUTPUT);
	pinMode(tdi3Pin, OUTPUT);
	pinMode(tdi4Pin, OUTPUT);
	pinMode(tdi5Pin, OUTPUT);
	pinMode(tdi6Pin, OUTPUT);
	pinMode(tdi7Pin, OUTPUT);
	pinMode(tdiClkPin, OUTPUT);

	/*HCDC DIGITAL OUTPUT PINS*/
	pinMode(tdo0Pin, INPUT);
	pinMode(tdo1Pin, INPUT);
	pinMode(tdo2Pin, INPUT);
	pinMode(tdo3Pin, INPUT);
	pinMode(tdo4Pin, INPUT);
	pinMode(tdo5Pin, INPUT);
	pinMode(tdo6Pin, INPUT);
	pinMode(tdo7Pin, INPUT);
	pinMode(tdoClkPin, INPUT);

	for (unsigned char tileRow=0; tileRow<2; tileRow++)
		for (unsigned char tileCol=0; tileCol<2; tileCol++)
			for (unsigned char selRow=0; selRow<11; selRow++)
				for (unsigned char selCol=(selRow==8?1:0); selCol<16; selCol++)
					for (unsigned char selLine=0; selLine<16; selLine++) {
						cfgTag[tileRow][tileCol][selRow][selCol][selLine>>3] = 255;
						cfgBuf[tileRow][tileCol][selRow][selCol][selLine] = 0;
					}

	/*create tiles*/
	// TODO
	tiles = new Tile[4] {
		Tile (this, tileRow0, tileCol0, spiSSPinBase+0, spiMisoPinBase+0, 8), // dummy ardAnaDiffChan
		Tile (this, tileRow0, tileCol1, spiSSPinBase+1, spiMisoPinBase+1, 8), // dummy ardAnaDiffChan
		Tile (this, tileRow1, tileCol0, spiSSPinBase+2, spiMisoPinBase+2, 8), // dummy ardAnaDiffChan
		Tile (this, tileRow1, tileCol1, spiSSPinBase+3, spiMisoPinBase+3, ardAnaDiffChanBase)
	};
	tally_dyn_mem <Tile[4]> ("Tile[4]");
}

Fabric::Chip::~Chip() { delete[] tiles; };

void Fabric::Chip::defaults(){
  for(int i=0; i < 4; i+=1){
    tiles[i].defaults();
  }
}
void Fabric::Chip::reset () {

	for (unsigned char tileRow=0; tileRow<2; tileRow++)
		for (unsigned char tileCol=0; tileCol<2; tileCol++)
			for (unsigned char selRow=0; selRow<11; selRow++)
				for (unsigned char selCol=(selRow==8?1:0); selCol<16; selCol++)
					for (unsigned char selLine=0; selLine<16; selLine++) {
						cfgTag[tileRow][tileCol][selRow][selCol][selLine>>3] = 255;
						cfgBuf[tileRow][tileCol][selRow][selCol][selLine] = 0;
					}

	/*create tiles*/
	delete[] tiles;
	tiles = new Tile[4] {
		Tile (this, tileRow0, tileCol0, spiSSPinBase+0, spiMisoPinBase+0, 8), // dummy ardAnaDiffChan
		Tile (this, tileRow0, tileCol1, spiSSPinBase+1, spiMisoPinBase+1, 8), // dummy ardAnaDiffChan
		Tile (this, tileRow1, tileCol0, spiSSPinBase+2, spiMisoPinBase+2, 8), // dummy ardAnaDiffChan
		Tile (this, tileRow1, tileCol1, spiSSPinBase+3, spiMisoPinBase+3, ardAnaDiffChanBase)
	};
	tally_dyn_mem <Tile[4]> ("Tile[4]");

}

/*Cache the vectors according to format choice*/
void Fabric::Chip::cacheVec (Vector vec) {
  sprintf(FMTBUF,
          "CFGTILE pos=(%d,%d,%d) data=%d",
          vec.selRow, vec.selCol, vec.selLine,
          vec.cfgTile);
  print_debug(FMTBUF);
	/*if arduino form, check that sram vector fields are within bounds*/
	if (vec.selRow<0||10<vec.selRow) error ("vec.selRow out of bounds");
	if (vec.selCol<0||15<vec.selCol) error ("vec.selCol out of bounds");
	if (vec.selRow==8&&vec.selCol==0) error ("vec cache cannot handle ctlr cmmds");
	if (vec.selLine<0||15<vec.selLine) error ("vec.selLine out of bounds");
	if (vec.cfgTile<0||255<vec.cfgTile) error ("vec.cfgTile out of bounds");
	if ( cfgBuf [vec.tileRowId] [vec.tileColId] [vec.selRow] [vec.selCol] [vec.selLine] != vec.cfgTile ) {
		if (vec.selRow==9) cfgLutLTag[vec.tileRowId][vec.tileColId]=true;
		if (vec.selRow==10) cfgLutRTag[vec.tileRowId][vec.tileColId]=true;
		// cfgTag [vec.tileRowId] [vec.tileColId] [vec.selRow] [vec.selCol] [vec.selLine>>3] |= (1<<(vec.selLine&7));
		bitSet(cfgTag [vec.tileRowId] [vec.tileColId] [vec.selRow] [vec.selCol] [vec.selLine>>3], vec.selLine&7);
		cfgBuf [vec.tileRowId] [vec.tileColId] [vec.selRow] [vec.selCol] [vec.selLine] = vec.cfgTile;
	}
}

/*Write out vectors according to format choice*/
void Fabric::Chip::writeVecs () {

	// first eight rows are more typical
	for (unsigned char tileRowIndx=0; tileRowIndx<2; tileRowIndx++)
		for (unsigned char tileColIndx=0; tileColIndx<2; tileColIndx++)
			for (unsigned char rowIndx=0; rowIndx<8; rowIndx++)
				for (unsigned char colIndx=0; colIndx<16; colIndx++)
					for (unsigned char tagIndx=0; tagIndx<2; tagIndx++) {
						unsigned char tag = cfgTag[tileRowIndx][tileColIndx][rowIndx][colIndx][tagIndx];
						for (unsigned char byteIndx=0; byteIndx<8; byteIndx++) {
							if (bitRead(tag,byteIndx)) { // if there are changes to make
								tiles[tileRowIndx*2+tileColIndx].spiDriveTile (rowIndx, colIndx, tagIndx*8+byteIndx, cfgBuf[tileRowIndx][tileColIndx][rowIndx][colIndx][tagIndx*8+byteIndx]);
							}
						}
						cfgTag[tileRowIndx][tileColIndx][rowIndx][colIndx][tagIndx] = 0;
					}

	// LUT clauses!
	// lut needs to be put in ctlr input mode with calls to lutParam0
	// (7,1) LUT configuration and crossbar messages (See LUT Bits [12:23])
	for (unsigned char tileRowIndx=0; tileRowIndx<2; tileRowIndx++) {
		for (unsigned char tileColIndx=0; tileColIndx<2; tileColIndx++) {

			// program values to LUT0
			if (cfgLutLTag[tileRowIndx][tileColIndx]) { // if there are changes to make
				unsigned char lutTempL = cfgBuf[tileRowIndx][tileColIndx][7][1][0];
				tiles[tileRowIndx*2+tileColIndx].slices[0].lut->setStart();
				for (unsigned char rowIndex = 0; rowIndex < 32; rowIndex++) {
					for (unsigned char colIndex = 0; colIndex < 8; colIndex++) {
						unsigned char addr = rowIndex + colIndex * 32;
						unsigned char endianAddr = endian (addr);
						unsigned char selRow = 0b1001;
						unsigned char selCol = (endianAddr&0xf0) >> 4;
						unsigned char selLine = (endianAddr&0x0f) >> 0;
						tiles[tileRowIndx*2+tileColIndx].spiDriveTile (selRow, selCol, selLine, cfgBuf[tileRowIndx][tileColIndx][selRow][selCol][selLine]);
					}
				}
				tiles[tileRowIndx*2+tileColIndx].spiDriveTile (7, 1, 0, lutTempL); // original setting
				cfgLutLTag[tileRowIndx][tileColIndx]=false;
			}

			// program values to LUT1
			if (cfgLutRTag[tileRowIndx][tileColIndx]) { // if there are changes to make
				unsigned char lutTempR = cfgBuf[tileRowIndx][tileColIndx][7][2][0];
				tiles[tileRowIndx*2+tileColIndx].slices[2].lut->setStart();
				for (unsigned char rowIndex = 0; rowIndex < 32; rowIndex++) {
					for (unsigned char colIndex = 0; colIndex < 8; colIndex++) {
						unsigned char addr = rowIndex + colIndex * 32;
						unsigned char endianAddr = endian (addr);
						unsigned char selRow = 0b1010;
						unsigned char selCol = (endianAddr&0xf0) >> 4;
						unsigned char selLine = (endianAddr&0x0f) >> 0;
						tiles[tileRowIndx*2+tileColIndx].spiDriveTile (selRow, selCol, selLine, cfgBuf[tileRowIndx][tileColIndx][selRow][selCol][selLine]);
					}
				}
				tiles[tileRowIndx*2+tileColIndx].spiDriveTile (7, 2, 0, lutTempR); // original setting
				cfgLutRTag[tileRowIndx][tileColIndx]=false;
			}
		}
	}
}

void Fabric::Chip::spiDriveChip (
	unsigned char selRow,
	unsigned char selCol,
	unsigned char selLine,
	unsigned char cfgTile
) const {
	digitalWriteDirect (tiles[0].spiSSPin, LOW);
	digitalWriteDirect (tiles[1].spiSSPin, LOW);
	digitalWriteDirect (tiles[2].spiSSPin, LOW);
	digitalWriteDirect (tiles[3].spiSSPin, LOW);
	spiDrive ( selRow, selCol, selLine, cfgTile );
	digitalWriteDirect (tiles[0].spiSSPin, HIGH);
	digitalWriteDirect (tiles[1].spiSSPin, HIGH);
	digitalWriteDirect (tiles[2].spiSSPin, HIGH);
	digitalWriteDirect (tiles[3].spiSSPin, HIGH);
}

int Fabric::Chip::spiDriveChip (
	const bool * vector
) const {
	digitalWriteDirect (tiles[0].spiSSPin, LOW);
	digitalWriteDirect (tiles[1].spiSSPin, LOW);
	digitalWriteDirect (tiles[2].spiSSPin, LOW);
	digitalWriteDirect (tiles[3].spiSSPin, LOW);
	unsigned char result = spiDrive (vector, tiles[0].spiMisoPin);
	digitalWriteDirect (tiles[0].spiSSPin, HIGH);
	digitalWriteDirect (tiles[1].spiSSPin, HIGH);
	digitalWriteDirect (tiles[2].spiSSPin, HIGH);
	digitalWriteDirect (tiles[3].spiSSPin, HIGH);
	return result;
}
