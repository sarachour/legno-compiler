#ifndef FU_BASECLASS
#define FU_BASECLASS

#include "block_state.h"



class Fabric::Chip::Tile::Slice::FunctionUnit {
	friend Slice;
	friend Connection;
	friend Vector;

	public:
		class Interface;
		virtual void setEnable ( bool enable ) { error("setEnable not implemented"); };
		void setParallelOut ( bool onOff ) const;
		Interface * in0;
		Interface * in1;
		Interface * out0;
		Interface * out1;
		Interface * out2;

    virtual void setAnaIrefNmos () const {
			error("setAnaIrefNmos not implemented");
		};
		virtual void setAnaIrefPmos () const {
			error("setAnaIrefPmos not implemented");
		};

    Fabric* getFabric() const{
      return parentSlice->parentTile->parentChip->parentFabric;
    }
    Fabric::Chip* getChip() const{
      return parentSlice->parentTile->parentChip;
    }
    Fabric::Chip::Tile* getTile() const{
      return parentSlice->parentTile;
    }
    void updateFu();

		const Slice * const parentSlice;
	private:
		class GenericInterface;
		FunctionUnit (
			Slice * parentSlice_,
			unit unitId_
		) :
			parentSlice(parentSlice_),
			unitId(unitId_)
		{
    };

		virtual ~FunctionUnit () {};
		virtual void setParam0 () const { error("setParam0 not implemented"); };
		virtual void setParam1 () const { error("setParam1 not implemented"); };
		virtual void setParam2 () const { error("setParam2 not implemented"); };
		virtual void setParam3 () const { error("setParam3 not implemented"); };
		virtual void setParam4 () const { error("setParam4 not implemented"); };
		virtual void setParam5 () const { error("setParam5 not implemented"); };

		// used for gain and initial condition range calibration
		const unit unitId;
};

class Fabric::Chip::Tile::Slice::FunctionUnit::Interface {
	friend FunctionUnit;
	friend ChipAdc;
	friend Dac;
	friend Fanout;
	friend Integrator;
	friend Multiplier;
	friend Connection;
	friend Vector;

	public:
  //virtual void setInv (
  //	bool inverse
  //) {
  //	error("setInv not implemented");
  //}; // whether output is negated
  //virtual void setRange (range_t range) {
  //	error("setRange not implemented");
  //};
		virtual ~Interface () {};
    FunctionUnit * const parentFu;
		const ifc ifcId;
		Interface * userSourceDest = NULL;
		Interface (
               FunctionUnit * parentFu,
               ifc ifcId
               ) :
    parentFu(parentFu),
			ifcId(ifcId)
      {};
	private:

    // TODO: incomplete implementation because multiple sources possible

};

#endif
