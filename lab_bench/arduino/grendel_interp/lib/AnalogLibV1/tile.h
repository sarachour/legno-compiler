class Fabric::Chip::Tile {
	friend Fabric;
	friend Chip;

	public:
		class Slice;
		bool calibrate() const;
    void defaults();
		void setParallelIn ( bool onOff ) const;
		/*Read serial digital data and the done bit*/
		void readSerial (
			unsigned char & adcData0,
			unsigned char & adcData1,
			bool & done
		) const;
		/*Read the exception bits*/
		void readExp (
			unsigned char & expVector
		) const;
		void spiDriveTile (
			unsigned char selRow,
			unsigned char selCol,
			unsigned char selLine,
			unsigned char cfgTile
		) const;

		Slice * slices;

		Chip * const parentChip;
	private:
		Tile (
			Chip * parentChip,
			tileRow tileRowId,
			tileCol tileColId,
			unsigned char spiSSPin,
			unsigned char spiMisoPin,
			unsigned char ardAnaDiffChanBase
		);
		~Tile();

		void controllerHelperTile (unsigned char selLine, unsigned char cfgTile) const;
		int spiDriveTile ( const bool * vector ) const;


		const tileRow tileRowId;
		const tileCol tileColId;
		const unsigned char spiSSPin; /*spi slave select*/
		const unsigned char spiMisoPin; /*spi master in slave out*/

		bool slice0DacOverride = false;
		bool slice1DacOverride = false;
		bool slice2DacOverride = false;
		bool slice3DacOverride = false;
};
