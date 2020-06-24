#ifndef DAC_H
#define DAC_H

#include "fu.h"
#include "calib_util.h"

typedef enum {
	// dacLo = 0,		/*the DAC block signal range is 2uA*/
	dacMid = 0,	/*the DAC block signal range is 2uA*/
	dacHi = 1		/*the DAC block signal range is 20uA*/
} dacRange;

typedef enum {
	lutL	= 0, /*signals from lutL are selected*/
	lutR	= 1, /*signals from lutR are selected*/
	extDac	= 2, /*signals from external are selected*/
	adc		= 3  /*signals from ADC are selected*/
} dacSel;

typedef struct {
  float alpha;
  float beta;
  float rsq;
} dac_model_t;

void fast_calibrate_dac(Fabric::Chip::Tile::Slice::Dac * aux_dac);

class Fabric::Chip::Tile::Slice::Dac : public Fabric::Chip::Tile::Slice::FunctionUnit {
	friend Slice;

	public:
		void setEnable ( bool enable ) override;
		void setRange (
			// default is 2uA mode
			range_t rng// 20 uA mode
		);
		void setSource (dac_source_t src);
		void setConstantCode (
			unsigned char constantCode
      // fixed point representation of desired constant
			// 0 to 255 are valid
		);
    void setConstant (
			float constant // floating point representation of desired constant
			// -10.0 to 10.0 are valid
		);
    void update(dac_state_t codes);
		void setInv (bool inverse ); // whether output is negated
    //measurement function
    profile_t measure(profile_spec_t);
    profile_t measureConstVal(profile_spec_t spec);
    //calibration function
    void calibrate(calib_objective_t obj);
    // fast measurement and make functions
    float fastMeasureValue(float& noise);
    float fastMakeValue(float value);
    void fastMakeDacModel();
    void defaults();

    static void computeInterval(dac_state_t& state,
                                port_type_t port, \
                                float& min, \
                                float& max);
    static float computeOutput(dac_state_t& codes);
    static float computeInput(dac_state_t& codes,float output);
    dac_state_t m_state;
    dac_state_t m_calib_state;
    dac_model_t m_dac_model;
    bool m_is_calibrated;
	private:
    //fast calibration utility
    float calibrateMinError();
    float calibrateMaxDeltaFit();
    float calibrateFast();
    float getLoss(calib_objective_t obj);
    //fast set source/measure utilities
    float fastMakeMedValue(float value, float max_error);
    float fastMakeHighValue(float value, float max_error);
    float fastMeasureHighValue(float& noise);
    float fastMeasureMedValue(float& noise);

		Dac (Slice * parentSlice);
		~Dac () override { delete out0; };
		/*Set enable, invert, range, clock select*/
		void setParam0 () const override;
		/*Set calDac, input select*/
		void setParam1 () const override;
    void setParam2 () const override {};
    void setParam3 () const override {};
    void setParam4 () const override {};
    void setParam5 () const override {};
		void setParamHelper (
			unsigned char selLine,
			unsigned char cfgTile
		) const;
		void setAnaIrefNmos () const override;
		void setAnaIrefPmos () const override {};

};


#endif
