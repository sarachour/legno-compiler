#ifndef CONNECTION_H
#define CONNECTION_H

class Fabric::Chip::Connection {
	friend Vector;

	public:
		Connection (
			Tile::Slice::FunctionUnit::Interface * sourceIfc,
			Tile::Slice::FunctionUnit::Interface * destIfc
		) :
			sourceIfc(sourceIfc),
			destIfc(destIfc),
			chip( sourceIfc ?
				*sourceIfc->parentFu->parentSlice->parentTile->parentChip :
				*destIfc->parentFu->parentSlice->parentTile->parentChip
			)
		{
			if (destIfc&&sourceIfc) {
				if (
					sourceIfc->parentFu->parentSlice->parentTile->parentChip->chipRowId != destIfc->parentFu->parentSlice->parentTile->parentChip->chipRowId ||
					sourceIfc->parentFu->parentSlice->parentTile->parentChip->chipColId != destIfc->parentFu->parentSlice->parentTile->parentChip->chipColId
				) error("cannot make connections between different chips");
			}
		};
		/*Generate selRow, selCol, selLine, setBit*/
		/*Set connection*/
		void setConn () const;
		/*Break connection*/
		void brkConn () const;

		Tile::Slice::FunctionUnit::Interface * const sourceIfc;
		Tile::Slice::FunctionUnit::Interface * const destIfc;

	private:
		Chip & chip;
};

#endif
