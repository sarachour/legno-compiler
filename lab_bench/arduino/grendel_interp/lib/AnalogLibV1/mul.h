#ifndef MUL_H
#define MUL_H

#include "fu.h"
#include "profile.h"

class Fabric::Chip::Tile::Slice::Multiplier : public Fabric::Chip::Tile::Slice::FunctionUnit {
	friend Slice;
	public:
		void setEnable ( bool enable ) override;
		void setGainCode (
			unsigned char gainCode // fixed point representation of desired gain
			// 0 to 255 are valid
		);
    void setGain(float gain);
		void setVga (
			bool vga // constant coefficient multiplier mode
		);

		void setRange (ifc port, range_t range);
    void update(mult_state_t codes);
    void defaults();
    static void computeInterval(mult_state_t& state,
                                port_type_t port, \
                                float& min, \
                                float& max);
    static float computeOutput(mult_state_t& m_codes, float in0, float in1);
    void calibrate (calib_objective_t obj);
    profile_t measure(profile_spec_t spec);

    mult_state_t m_state;
	private:
    profile_t measureVga(profile_spec_t spec);
    profile_t measureOscVga(profile_spec_t spec);
    profile_t measureMult(profile_spec_t spec);

    float getLoss(calib_objective_t obj,
                  Dac * val0_dac,
                  Dac * val1_dac,
                  Dac * ref_dac,
                  bool ignore_bias);
    void calibrateHelperFindBiasCodes(cutil::calib_table_t& tbl, int stride,
                                      Dac * val0_dac,
                                      Dac * val1_dac,
                                      Dac * ref_dac,
                                      int bounds[6],
                                      float pos,
                                      float target_pos,
                                      float neg,
                                      float target_neg);
    float calibrateHelperMult(Dac * val0_dac,
                              Dac * val1_dac,
                              Dac * ref_dac,
                              float* observations,
                              float* expected,
                              int& npts);
    float calibrateHelperVga(Dac * val_dac,
                             Dac * ref_dac,
                             float* observations,
                             float* expected,
                             int& npts);

    float calibrateMinError(Dac * val0_dac,
                            Dac * val1_dac,
                            Dac * ref_dac);
    float calibrateMinErrorVga(Dac * val_dac,
                               Dac * ref_dac);
    float calibrateMinErrorMult(Dac * val0_dac,
                                Dac * val1_dac,
                                Dac * ref_dac);
    float calibrateMaxDeltaFit(Dac * val0_dac,
                               Dac * val1_dac,
                               Dac * ref_dac,
                               bool ignore_bias);
    float calibrateMaxDeltaFitVga(Dac * val_dac,
                                  Dac * ref_dac,
                                  bool ignore_bias);
    float calibrateMaxDeltaFitMult(Dac * val0_dac,
                                Dac * val1_dac,
                                   Dac * ref_dac,
                                   bool ignore_bias);
		Multiplier (Slice * parentSlice, unit unitId);
		~Multiplier () override {
			delete out0;
			delete in0;
			delete in1;
		};
		/*Set enable, input 1 range, input 2 range, output range*/
		void setParam0 () const override;
		/*Set calDac, enable variable gain amplifer mode*/
		void setParam1 () const override;
		/*Set gain if VGA mode*/
		void setParam2 () const override;
		/*Set calOutOs*/
		void setParam3 () const override;
		/*Set calInOs1*/
		void setParam4 () const override;
		/*Set calInOs2*/
		void setParam5 () const override;
		/*Helper function*/
		void setParamHelper (
			unsigned char selLine,
			unsigned char cfgTile
		) const;
		void setAnaIrefNmos () const override;
		void setAnaIrefPmos () const override;
		//bool vga = false;
		//unsigned char gainCode = 128;
	public:
		//unsigned char anaIrefPmos = 3;
};


#endif
