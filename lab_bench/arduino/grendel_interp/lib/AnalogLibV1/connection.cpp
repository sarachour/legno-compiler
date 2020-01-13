#include "AnalogLib.h"

/*Set connection*/
void Fabric::Chip::Connection::setConn () const {

	if (sourceIfc->userSourceDest) sourceIfc->userSourceDest->userSourceDest=NULL;
	sourceIfc->userSourceDest=destIfc;
	destIfc->userSourceDest=sourceIfc;

	/*Generate selRow, selCol, selLine, setBit*/
	Vector vec = Vector (this);

	/*in current mode, each output should only connect to one input*/
	/*erase other destinations sharing same line*/
	// the number of rows to nullify depends on whether global
	if (vec.global) {
		// global
		for (unsigned char row=0; row<5; row++) {
			/*erase row*/
			chip.cacheVec ( vec.nullNeighborRow(tileRow0, row) );
			chip.cacheVec ( vec.nullNeighborRow(tileRow1, row) );
		}
	} else {
		// local
		for (unsigned char row=0; row<6; row++) {
			/*erase row*/
			chip.cacheVec ( vec.nullNeighborRow(row) );
		}
	}
	switch (sourceIfc->parentFu->unitId) {
		case chipInp:
      sourceIfc->parentFu->parentSlice->chipInput->setEnable(true); break;
		case unitDac:
      sourceIfc->parentFu->parentSlice->dac->setEnable(true); break;
		case unitMulL:
      sourceIfc->parentFu->parentSlice->muls[0].setEnable(true); break;
		case unitMulR:
      sourceIfc->parentFu->parentSlice->muls[1].setEnable(true); break;
		case unitInt:
			sourceIfc->parentFu->parentSlice->integrator->setEnable(true);
			sourceIfc->parentFu->parentSlice->integrator->setException(true);
		break;
		case unitFanL:
      sourceIfc->parentFu->parentSlice->fans[0].setEnable(true);
			if (sourceIfc->ifcId==out2Id)
        sourceIfc->parentFu->parentSlice->fans[0].setThird(true);
      break;
		case unitFanR:
      sourceIfc->parentFu->parentSlice->fans[1].setEnable(true);
			if (sourceIfc->ifcId==out2Id)
        sourceIfc->parentFu->parentSlice->fans[1].setThird(true);
		break;
		default: break;
	}
	switch (destIfc->parentFu->unitId) {
		case unitMulL:
      destIfc->parentFu->parentSlice->muls[0].setEnable(true); break;
		case unitMulR:
      destIfc->parentFu->parentSlice->muls[1].setEnable(true); break;
		case unitInt: 
			destIfc->parentFu->parentSlice->integrator->setEnable(true);
			destIfc->parentFu->parentSlice->integrator->setException(true);
		break;
		case unitFanL:
      destIfc->parentFu->parentSlice->fans[0].setEnable(true); break;
		case unitFanR:
      destIfc->parentFu->parentSlice->fans[1].setEnable(true); break;
		case unitAdc:
      destIfc->parentFu->parentSlice->adc->setEnable(true); break;
		default: break;
	}

	// Serial.println("; selRow ="); Serial.println(vec.selRow);
	// Serial.println("; selCol ="); Serial.println(vec.selCol);
	// Serial.println("; selLine ="); Serial.println(vec.selLine);
	// Serial.println("; setBit ="); Serial.println(vec.cfgTile);
	chip.cacheVec (vec);
}

/*Break connection*/
void Fabric::Chip::Connection::brkConn () const {

	sourceIfc->userSourceDest=NULL;
	destIfc->userSourceDest=NULL;

	/*Generate selRow, selCol, selLine, setBit*/
	Vector vec = Vector (this);

	switch (sourceIfc->parentFu->unitId) {
		case chipInp:
      sourceIfc->parentFu->parentSlice->chipInput->setEnable(false); break;
		case unitDac:
      sourceIfc->parentFu->parentSlice->dac->setEnable(false); break;
		case unitMulL:
      sourceIfc->parentFu->parentSlice->muls[0].setEnable(false); break;
		case unitMulR:
      sourceIfc->parentFu->parentSlice->muls[1].setEnable(false); break;
		case unitInt:
			sourceIfc->parentFu->parentSlice->integrator->setEnable(false);
			sourceIfc->parentFu->parentSlice->integrator->setException(false);
		break;
		case unitFanL: //sourceIfc->parentFu->parentSlice->fans[0].setEnable(false);
			if (sourceIfc->ifcId==out2Id) sourceIfc->parentFu->parentSlice->fans[0].setThird(false);
		break;
		case unitFanR: //sourceIfc->parentFu->parentSlice->fans[1].setEnable(false);
			if (sourceIfc->ifcId==out2Id) sourceIfc->parentFu->parentSlice->fans[1].setThird(false);
		break;
		default: break;
	}

	chip.cacheVec (vec.null());
}

unsigned char localSelRow (
	slice destSlice,
	unit destUnit
) {
	switch (destUnit) {
		case chipInp: error ("chipInp destUnit"); break;
		case tileInp0: /*FALLTHROUGH*/
		case tileInp1: /*FALLTHROUGH*/
		case tileInp2: /*FALLTHROUGH*/
		case tileInp3: error ("global logic error"); break;
		case unitDac: error ("unitDac destUnit"); break;
		case unitAdc: switch (destSlice) {
			case slice0: return (4);
			case slice1: error ("invalid slice. Only even slices have ADCs"); break; 
			case slice2: return (5);
			case slice3: error ("invalid slice. Only even slices have ADCs"); break;
		}
		case unitLut: error ("unitLut destUnit"); break;
		case tileOut0: /*FALLTHROUGH*/
		case tileOut1: /*FALLTHROUGH*/
		case tileOut2: /*FALLTHROUGH*/
		case tileOut3: switch (destSlice) {
			case slice0: /*FALLTHROUGH*/
			case slice1: return (1);
			case slice2: /*FALLTHROUGH*/
			case slice3: return (0);
		}
		case chipOut: error ("global logic error"); break;
		default: switch (destSlice) {
			case slice0: return (2);
			case slice1: return (3);
			case slice2: return (4);
			case slice3: return (5);
		}
	}
	error ("global logic error");
	return 0;
}

unsigned char localSelCol (
	slice sourceSlice,
	unit sourceUnit
) {
	switch (sourceUnit) {
		case chipInp: error ("global logic error"); break;
		case tileInp0: /*FALLTHROUGH*/
		case tileInp1: switch (sourceSlice) {
			case slice0: return (3);
			// HCDC 2 new ones follow
			case slice1: /*FALLTHROUGH*/
			case slice2: /*FALLTHROUGH*/
			case slice3: return (5);
			default: error ("sourceSlice"); break;
		}
		case tileInp2: /*FALLTHROUGH*/
		case tileInp3: switch (sourceSlice) {
			case slice0: return (4);
			// HCDC 2 new ones follow
			case slice1: /*FALLTHROUGH*/
			case slice2: /*FALLTHROUGH*/
			case slice3: return (5);
			default: error ("sourceSlice"); break;
		}
		case unitMulL: return (3);
		case unitMulR: return (4);
		case unitDac: switch (sourceSlice) {
			// HCDC 2 new DAC:
			case slice0: return (2);
			case slice1: return (2);
			// HCDC 2 new DAC:
			case slice2: return (5);
			case slice3: return (5);
			default: error ("sourceSlice"); break;
		}
		case unitInt: return (2);
		case unitFanL: return (0);
		case unitFanR: return (1);
		case unitAdc: error ("unitAdc sourceUnit"); break;
		case unitLut: error ("unitLut destUnit"); break;
		case tileOut0: /*FALLTHROUGH*/
		case tileOut1: /*FALLTHROUGH*/
		case tileOut2: /*FALLTHROUGH*/
		case tileOut3: error ("global logic error"); break;
		case chipOut: error ("chipOut sourceUnit"); break;
		default: error ("sourceUnit"); break;
	}
	error ("global logic error");
	return 0;
}

unsigned char localSelLine (
	slice sourceSlice,
	unit sourceUnit,
	ifc sourceIfc
) {
	switch (sourceUnit) {
		case chipInp: error ("global logic error"); break;
		case tileInp0: switch (sourceSlice) {
			case slice0: return (10);
			// HCDC 2 new ones follow
			case slice1: return (2);
			case slice2: return (6);
			case slice3: return (10);
			default: error ("sourceSlice"); break;
		}
		case tileInp1: switch (sourceSlice) {
			case slice0: return (11);
			// HCDC 2 new ones follow
			case slice1: return (3);
			case slice2: return (7);
			case slice3: return (11);
			default: error ("sourceSlice"); break;
		}
		case tileInp2: switch (sourceSlice) {
			case slice0: return (10);
			// HCDC 2 new ones follow
			case slice1: return (4);
			case slice2: return (8);
			case slice3: return (12);
			default: error ("sourceSlice"); break;
		}
		case tileInp3: switch (sourceSlice) {
			case slice0: return (11);
			// HCDC 2 new ones follow
			case slice1: return (5);
			case slice2: return (9);
			case slice3: return (13);
			default: error ("sourceSlice"); break;
		}
		case unitMulL: /*FALLTHROUGH*/
		case unitMulR: switch (sourceSlice) {
			case slice0: return (6);
			case slice1: return (7);
			case slice2: return (8);
			case slice3: return (9);
			default: error ("sourceSlice"); break;
		}
		case unitDac: switch (sourceSlice) {
			case slice0: return (9);
			case slice1: return (10);
			case slice2: return (14);
			case slice3: return (15);
			default: error ("unitDac sourceSlice"); break;
		}
		case unitInt: switch (sourceSlice) {
			case slice0: return (5);
			case slice1: return (6);
			case slice2: return (7);
			case slice3: return (8);
			default: error ("sourceSlice"); break;
		}
		case unitFanL: /*FALLTHROUGH*/
		case unitFanR: switch (sourceSlice) {
			case slice0: switch (sourceIfc) {
				case out0Id: return (4);
				case out1Id: return (5);
				case out2Id: return (6);
				default: error ("sourceIfc"); break;
			}
			case slice1: switch (sourceIfc) {
				case out0Id: return (7);
				case out1Id: return (8);
				case out2Id: return (9);
				default: error ("sourceIfc"); break;
			}
			case slice2: switch (sourceIfc) {
				case out0Id: return (10);
				case out1Id: return (11);
				case out2Id: return (12);
				default: error ("sourceIfc"); break;
			}
			case slice3: switch (sourceIfc) {
				case out0Id: return (13);
				case out1Id: return (14);
				case out2Id: return (15);
				default: error ("sourceIfc"); break;
			}
			default: error ("sourceSlice"); break;
		}
		case unitAdc: error ("unitAdc sourceUnit"); break;
		case unitLut: error ("unitLut sourceUnit"); break;
		case tileOut0: /*FALLTHROUGH*/
		case tileOut1: /*FALLTHROUGH*/
		case tileOut2: /*FALLTHROUGH*/
		case tileOut3: error ("global logic error"); break;
		case chipOut: error ("chipOut sourceUnit"); break;
		default: error ("sourceUnit"); break;
	}
	error ("global logic error");
	return 0;
}

unsigned char localSetBit (
	slice destSlice,
	unit destUnit,
	ifc destIfc
) {
	switch (destUnit) {
		case chipInp: error ("chipInp destUnit"); break;
		case tileInp0: /*FALLTHROUGH*/
		case tileInp1: /*FALLTHROUGH*/
		case tileInp2: /*FALLTHROUGH*/
		case tileInp3: error ("global logic error"); break;
		case unitMulL: switch (destIfc) {
			case in0Id: return (3);
			case in1Id: return (4);
			default: error ("destIfc"); break;
		}
		case unitMulR: switch (destIfc) {
			case in0Id: return (5);
			case in1Id: return (6);
			default: error ("destIfc"); break;
		}
		case unitDac: error ("unitDac destUnit"); break;
		case unitInt: return (2);
		case unitFanL: return (0);
		case unitFanR: return (1);
		case unitAdc: return (7);
		case unitLut: error ("unitLut destUnit"); break;
		case tileOut0: switch (destSlice) {
			case slice0: return (7);
			case slice1: return (3);
			case slice2: return (7);
			case slice3: return (3);
			default: error ("destSlice"); break;
		}
		case tileOut1: switch (destSlice) {
			case slice0: return (6);
			case slice1: return (2);
			case slice2: return (6);
			case slice3: return (2);
			default: error ("destSlice"); break;
		}
		case tileOut2: switch (destSlice) {
			case slice0: return (5);
			case slice1: return (1);
			case slice2: return (5);
			case slice3: return (1);
			default: error ("destSlice"); break;
		}
		case tileOut3: switch (destSlice) {
			case slice0: return (4);
			case slice1: return (0);
			case slice2: return (4);
			case slice3: return (0);
			default: error ("destSlice"); break;
		}
		case chipOut: error ("global logic error"); break;
		default: error ("destUnit"); break;
	}
	error ("global logic error");
	return 0;
}

/*Generate selRow, selCol, selLine, setBit*/
/*May need to use pointer return type*/
Fabric::Chip::Vector::Vector (const Chip::Connection * connection) {

	tileRowId = connection->destIfc->parentFu->parentSlice->parentTile->tileRowId;
	tileColId = connection->sourceIfc->parentFu->parentSlice->parentTile->tileColId;

	global = (
		connection->sourceIfc->parentFu->unitId == chipInp ||
		connection->destIfc->parentFu->unitId == tileInp0 ||
		connection->destIfc->parentFu->unitId == tileInp1 ||
		connection->destIfc->parentFu->unitId == tileInp2 ||
		connection->destIfc->parentFu->unitId == tileInp3 ||
		connection->sourceIfc->parentFu->unitId == tileOut0 ||
		connection->sourceIfc->parentFu->unitId == tileOut1 ||
		connection->sourceIfc->parentFu->unitId == tileOut2 ||
		connection->sourceIfc->parentFu->unitId == tileOut3 ||
		connection->destIfc->parentFu->unitId == chipOut
	);
	if ( !global && connection->sourceIfc->parentFu->parentSlice->parentTile->tileRowId != connection->destIfc->parentFu->parentSlice->parentTile->tileRowId ) {error ("cannot make local connection bewteen units not in same tile");}
	if ( !global && connection->sourceIfc->parentFu->parentSlice->parentTile->tileColId != connection->destIfc->parentFu->parentSlice->parentTile->tileColId ) {error ("cannot make local connection bewteen units not in same tile");}

	/*DETERMINE SEL_ROW*/
	if ( !global ) {
		// all connections possible use localSelRow
		selRow = localSelRow (
			connection->destIfc->parentFu->parentSlice->sliceId,
			connection->destIfc->parentFu->unitId
		);
	} else {
		// only tileInp and chipOut are valid dests use globalSelRow
		switch (connection->destIfc->parentFu->unitId) {
			case tileInp0: /*FALLTHROUGH*/
			case tileInp1: /*FALLTHROUGH*/
			case tileInp2: /*FALLTHROUGH*/
			case tileInp3: switch (connection->destIfc->parentFu->parentSlice->sliceId) {
				case slice0: /*FALLTHROUGH*/
				case slice1: selRow = connection->destIfc->parentFu->parentSlice->parentTile->tileColId==tileCol0 ? 0 : 2; break; // global
				case slice2: /*FALLTHROUGH*/
				case slice3: selRow = connection->destIfc->parentFu->parentSlice->parentTile->tileColId==tileCol0 ? 1 : 3; break; // global
			} break;
			case chipOut: selRow = 4; break;
			default: error ("global logic error"); break;
		}
	}

	/*DETERMINE SEL_COL*/
	if ( !global ) {
		// all connections possible use localSelCol
		selCol = localSelCol (
			connection->sourceIfc->parentFu->parentSlice->sliceId,
			connection->sourceIfc->parentFu->unitId
		);
	} else {
		// only tileOut and chipInp are valid sources use globalSelCol
		switch (connection->sourceIfc->parentFu->unitId) {
			case chipInp: selCol = 15; break;
			case tileOut0: selCol = connection->sourceIfc->parentFu->parentSlice->parentTile->tileRowId==tileRow0 ? 13 : 14; break;
			case tileOut1: selCol = connection->sourceIfc->parentFu->parentSlice->parentTile->tileRowId==tileRow0 ? 13 : 14; break;
			case tileOut2: selCol = connection->sourceIfc->parentFu->parentSlice->parentTile->tileRowId==tileRow0 ? 13 : 14; break;
			case tileOut3: selCol = connection->sourceIfc->parentFu->parentSlice->parentTile->tileRowId==tileRow0 ? 13 : 14; break;
			default: error ("global logic error"); break;
		}
	}

	/*DETERMINE SEL_LINE*/
	if ( !global ) {
		// all connections possible use localSelLine
		selLine = localSelLine (
			connection->sourceIfc->parentFu->parentSlice->sliceId,
			connection->sourceIfc->parentFu->unitId,
			connection->sourceIfc->ifcId
		);
	} else {
		// only tileOut and chipInp are valid sources use globalSelLine
		switch (connection->sourceIfc->parentFu->unitId) {
			case chipInp: switch (connection->sourceIfc->parentFu->parentSlice->sliceId) {
				case slice0: selLine = connection->sourceIfc->parentFu->parentSlice->parentTile->tileRowId==tileRow0 ? 0 : 4; break;
				case slice1: selLine = connection->sourceIfc->parentFu->parentSlice->parentTile->tileRowId==tileRow0 ? 1 : 5; break;
				case slice2: selLine = connection->sourceIfc->parentFu->parentSlice->parentTile->tileRowId==tileRow0 ? 2 : 6; break;
				case slice3: selLine = connection->sourceIfc->parentFu->parentSlice->parentTile->tileRowId==tileRow0 ? 3 : 7; break;
				default: error ("sourceSlice"); break;
			} break;
			case tileOut0: switch (connection->sourceIfc->parentFu->parentSlice->sliceId) {
				case slice0: selLine = 0; break;
				case slice1: selLine = 4; break;
				case slice2: selLine = 8; break;
				case slice3: selLine = 12; break;
				default: error ("sourceSlice"); break;
			} break;
			case tileOut1: switch (connection->sourceIfc->parentFu->parentSlice->sliceId) {
				case slice0: selLine = 1; break;
				case slice1: selLine = 5; break;
				case slice2: selLine = 9; break;
				case slice3: selLine = 13; break;
				default: error ("sourceSlice"); break;
			} break;
			case tileOut2: switch (connection->sourceIfc->parentFu->parentSlice->sliceId) {
				case slice0: selLine = 2; break;
				case slice1: selLine = 6; break;
				case slice2: selLine = 10; break;
				case slice3: selLine = 14; break;
				default: error ("sourceSlice"); break;
			} break;
			case tileOut3: switch (connection->sourceIfc->parentFu->parentSlice->sliceId) {
				case slice0: selLine = 3; break;
				case slice1: selLine = 7; break;
				case slice2: selLine = 11; break;
				case slice3: selLine = 15; break;
				default: error ("sourceSlice"); break;
			} break;
			default: error ("global logic error"); break;
		}
	}

	/*DETERMINE SET_BIT*/
	if ( !global ) {
		// all connections possible use localSetBit
		setBit( localSetBit (
			connection->destIfc->parentFu->parentSlice->sliceId,
			connection->destIfc->parentFu->unitId,
			connection->destIfc->ifcId
		));
	} else {
		// only tileInp and chipOut are valid dests use globalSetBit
		switch (connection->destIfc->parentFu->unitId) {
			case tileInp0: switch (connection->destIfc->parentFu->parentSlice->sliceId) {
				case slice0: setBit (0); break;
				case slice1: setBit (4); break;
				case slice2: setBit (0); break;
				case slice3: setBit (4); break;
				default: error ("destSlice"); break;
			} break;
			case tileInp1: switch (connection->destIfc->parentFu->parentSlice->sliceId) {
				case slice0: setBit (1); break;
				case slice1: setBit (5); break;
				case slice2: setBit (1); break;
				case slice3: setBit (5); break;
				default: error ("destSlice"); break;
			} break;
			case tileInp2: switch (connection->destIfc->parentFu->parentSlice->sliceId) {
				case slice0: setBit (2); break;
				case slice1: setBit (6); break;
				case slice2: setBit (2); break;
				case slice3: setBit (6); break;
				default: error ("destSlice"); break;
			} break;
			case tileInp3: switch (connection->destIfc->parentFu->parentSlice->sliceId) {
				case slice0: setBit (3); break;
				case slice1: setBit (7); break;
				case slice2: setBit (3); break;
				case slice3: setBit (7); break;
				default: error ("destSlice"); break;
			} break;
			case chipOut: switch (connection->destIfc->parentFu->parentSlice->sliceId) {
				case slice0: setBit (connection->destIfc->parentFu->parentSlice->parentTile->tileColId==tileCol0 ? 7 : 3); break;
				case slice1: setBit (connection->destIfc->parentFu->parentSlice->parentTile->tileColId==tileCol0 ? 6 : 2); break;
				case slice2: setBit (connection->destIfc->parentFu->parentSlice->parentTile->tileColId==tileCol0 ? 5 : 1); break;
				case slice3: setBit (connection->destIfc->parentFu->parentSlice->parentTile->tileColId==tileCol0 ? 4 : 0); break;
				default: error ("destSlice"); break;
			} break;
			default: error ("global logic error"); break;
		}
	}
}
