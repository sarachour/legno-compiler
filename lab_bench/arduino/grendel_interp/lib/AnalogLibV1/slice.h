#ifndef SLICE_H
#define SLICE_H

int slice_to_int(const slice slc);
class Fabric::Chip::Tile::Slice {
	friend Tile;
	friend Connection;
	friend Vector;

	public:
		class FunctionUnit;
		class ChipInput;
		class TileInOut;
		class Dac;
		class Multiplier;
		class Integrator;
		class Fanout;
		class ChipAdc;
		class LookupTable;
		class ChipOutput;

		ChipInput * chipInput;
		TileInOut * tileInps;
		Dac * dac;
		Multiplier * muls;
		Integrator * integrator;
		Fanout * fans;
		ChipAdc * adc;
		LookupTable * lut;
		TileInOut * tileOuts;
		ChipOutput * chipOutput;

    void defaults();
		Tile * const parentTile;
    const slice sliceId;
	private:
		Slice (
			Tile * parentTile,
			slice sliceId,
			unsigned char ardAnaDiffChan
		);
		~Slice ();
		/*ANALOG INPUT PINS*/
		const unsigned char ardAnaDiffChan; /*ANALOG OUTAna*/
};


#endif
