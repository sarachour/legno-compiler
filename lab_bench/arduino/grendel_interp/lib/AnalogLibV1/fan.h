#ifndef FANOUT_H
#define FANOUT_H

#include "fu.h"

class Fabric::Chip::Tile::Slice::Fanout : public Fabric::Chip::Tile::Slice::FunctionUnit {
	friend Slice;

	public:
		void setEnable ( bool enable ) override;
		void setRange (
			range_t range// 20uA mode
			// 20uA mode results in more ideal behavior in terms of phase shift but consumes more power
			// this setting should match the unit that gives the input to the fanout
		);
		void setInv ( ifc port, bool inverse );
		void setThird (
			bool third // whether third output is on
		);
    static void computeInterval(fanout_state_t& state,
                                port_type_t port, \
                                float& min, \
                                float& max);
    static float computeOutput(fanout_state_t& state,ifc index,float in);
		void calibrate (calib_objective_t obj);
    void defaults();
    void update(fanout_state_t codes){
      m_state = codes;
      updateFu();
    }
		profile_t measure(profile_spec_t spec);
    fanout_state_t m_state;
	private:
		class FanoutOut;
		Fanout (Slice * parentSlice, unit unitId);
		~Fanout () override {
			delete in0;
			delete out0;
			delete out1;
			delete out2;
		};
    profile_t measureConstVal(profile_spec_t spec);
    void measureZero(float& bias0, float& bias1, float& bias2);
    float calibrateMinError(Fabric::Chip::Tile::Slice::Dac * val_dac,
                            Fabric::Chip::Tile::Slice::Dac * ref_dac,
                            ifc out_id);
    float calibrateMaxDeltaFit(Fabric::Chip::Tile::Slice::Dac * val_dac,
                               Fabric::Chip::Tile::Slice::Dac * ref_dac,
                               ifc out_id);
    float calibrateFast(Fabric::Chip::Tile::Slice::Dac * val_dac,
                        Fabric::Chip::Tile::Slice::Dac * ref_dac,
                        ifc out_id);
    float getLoss(calib_objective_t obj,
                   Fabric::Chip::Tile::Slice::Dac * val_dac,
                   Fabric::Chip::Tile::Slice::Dac * ref_dac,
                   ifc out_id);

		/*Set enable, range*/
		void setParam0 () const override;
		/*Set calDac1, invert output 1*/
		void setParam1 () const override;
		/*Set calDac2, invert output 2*/
		void setParam2 () const override;
		/*Set calDac3, invert output 3, enable output 3*/
		void setParam3 () const override;
		void setParam4 () const override {};
		void setParam5 () const override {};
		/*Helper function*/
		void setParamHelper (
			unsigned char selLine,
			unsigned char cfgTile
		) const;
		void setAnaIrefNmos () const override;
		void setAnaIrefPmos () const override;

		// generally does not influence fanout performance
		// anaIrefNmos is remapped in SW to anaIrefPmos
		// const unsigned char anaIrefPmos = 3;
};

class Fabric::Chip::Tile::Slice::Fanout::FanoutOut : public Fabric::Chip::Tile::Slice::FunctionUnit::Interface  {
	friend Fanout;

	public:
		void setInv ( bool inverse );
	private:
		FanoutOut (Fanout * parentFu, ifc ifcId) :
			Interface(parentFu, ifcId),
			parentFanout(parentFu)
		{};
		Fanout * const parentFanout;
};

#endif
