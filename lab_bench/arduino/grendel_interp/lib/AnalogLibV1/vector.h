/*Crossbar switch cell specifies which switch to set*/
class Fabric::Chip::Vector {
	friend Chip;
	friend Tile;

	private:
		/*TILE SPECIFIC*/
		tileRow tileRowId;
		tileCol tileColId;
		bool global;
		Vector (
			const Connection * connection
		);
		Vector nullNeighborRow (
			tileRow tileRowId_,
			unsigned char row_
		) const {
			return Vector (
				// parentChip, // own
				tileRowId_, // param
				tileColId, // own
				row_, // param
				selCol, // own
				selLine, // own
				0 // nullify
			);
		};
		Vector nullNeighborRow (
			unsigned char row_
		) const {
			return Vector (
				// parentChip, // own
				tileRowId, // own
				tileColId, // own
				row_, // param
				selCol, // own
				selLine, // own
				0 // nullify
			);
		};
		Vector null () const {
			return Vector (
				// parentChip, // own
				tileRowId, // own
				tileColId, // own
				selRow, // own
				selCol, // own
				selLine, // own
				0 // nullify
			);
		};
		Vector (
			const Chip::Tile::Slice::FunctionUnit & fu,
			unsigned char selRow_,
			unsigned char selCol_,
			unsigned char selLine_,
			unsigned char cfgTile_
		) :
			tileRowId(fu.parentSlice->parentTile->tileRowId),
			tileColId(fu.parentSlice->parentTile->tileColId),
			global(false),
			selRow(selRow_),
			selCol(selCol_),
			selLine(selLine_),
			cfgTile(cfgTile_)
		{};

		/*MISC*/
		unsigned char selRow;
		unsigned char selCol;
		unsigned char selLine;
		unsigned char cfgTile;

		void setBit (unsigned char setBit) {
			if (setBit<0||7<setBit) {Serial.println("E: setBit out of bounds.\n"); exit(1);}
			unsigned char exponent = 7-setBit;
			cfgTile = 1<<exponent;
		};

		Vector (
			tileRow tileRowId_,
			tileCol tileColId_,
			unsigned char selRow_,
			unsigned char selCol_,
			unsigned char selLine_,
			unsigned char cfgTile_
		) :
			tileRowId(tileRowId_),
			tileColId(tileColId_),
			global(false),
			selRow(selRow_),
			selCol(selCol_),
			selLine(selLine_),
			cfgTile(cfgTile_)
		{};
};

/*Auxiliary function for converting between endian formats for 8 bit values*/
unsigned char endian (unsigned char input);