#ifndef HDAC_ADC_H
#define HDAC_ADC_H

#include "fu.h"

typedef enum {
	adcLo = 0,		/*2uA*/
	adcMid = 0,	/*2uA*/
	adcHi = 1		/*20uA*/
} adcRange;

typedef enum {
	ns11_5 =	0, /*11.5 ns delay (normal operation)*/
	ns9_7 = 	1, /*9.7 ns delay*/
	ns7_8 = 	2, /*7.8 ns delay*/
	ns5_8 = 	3  /*5.8 ns delay*/
} adcDelay;

typedef enum {
	ns3 =		0, /*3ns is the default*/
	ns6 =		1  /*6ns trigger delay*/
} adcTrigDelay;

typedef enum {
	nA100 = 0, /*IFS = 100nA*/
	nA200 = 1, /*IFS = 200nA*/
	nA300 = 2, /*IFS = 300nA*/
	nA400 = 3  /*IFS = 400nA*/
} adcCalCompFs;

class Fabric::Chip::Tile::Slice::ChipAdc : public Fabric::Chip::Tile::Slice::FunctionUnit {
	friend Slice;
	public:
		void setEnable ( bool enable ) override;
		void setRange (
			// default is 2uA mode
			range_t range // 20 uA mode
		);
    static float digitalCodeToValue(float input);
    static float digitalOffsetToValue(float input);
    static float computeOutput(adc_state_t& config, float input);
    static void computeInterval(adc_state_t& config, port_type_t port,
                                 float& min, float& max);
		unsigned char getData () const;
		unsigned char getStatusCode() const;
		bool getException() const;
    void update(adc_state_t codes){m_state= codes; updateFu();}
		void calibrate (calib_objective_t obj);

		profile_t measure(profile_spec_t spec);
		profile_t measureConstVal(profile_spec_t spec);
    void defaults();
		void setAnaIrefNmos () const override;

    adc_state_t m_state;
	private:
    bool testValidity(Fabric::Chip::Tile::Slice::Dac * val_dac);
    float calibrateMinError(Fabric::Chip::Tile::Slice::Dac * val_dac);
    float calibrateMaxDeltaFit(Fabric::Chip::Tile::Slice::Dac * val_dac);
    float calibrateFast(Fabric::Chip::Tile::Slice::Dac * val_dac);
    float getLoss(calib_objective_t obj, Fabric::Chip::Tile::Slice::Dac * val_dac);
		ChipAdc (Slice * parentSlice);
		~ChipAdc () override { delete in0; };
    void setTestParams (
                        bool testEn, /*Configure the entire block in testing mode so that I2V and A/D can be tested individually*/
                        bool testAdc, /*Testing the ADC individually.*/
                        bool testIv, /*Testing the I2V individually.*/
                        bool testRs, /*Testing the rstring individually.*/
                        bool testRsInc /*Configure the counter for upward or downward increments during set up for testing R-string separately (w/ cfgCalEN=1)*/
                        );
		/*Set enable, range, delay, decRst*/
		void setParam0 () const override;
		/*Set calibration enable, calCompUpperEn, calIv*/
		void setParam1 () const override;
		/*Set calCompLower, calCompLowerFs*/
		void setParam2 () const override;
		/*Set calCompUpper, calCompUpperFs*/
		void setParam3 () const override;
		/*Set testEn, testAdc, testIv, testRs, testRsInc*/
    void setParam4 () const override;
    void setParam5() const override {};
		/*Helper function*/
		void setParamHelper (
			unsigned char selLine,
			unsigned char cfgTile
		) const;
		void setAnaIrefPmos () const override;

    /*
		unsigned char calI2V = 31;
		// anaIrefI2V is remapped in SW to AnaIrefDacNmos

		unsigned char calCompLower = 31;
		adcCalCompFs calCompLowerFs = nA100;
		const unsigned char anaIref1Pmos = 4;

		unsigned char calCompUpper = 31;
		adcCalCompFs calCompUpperFs = nA100;
		const unsigned char anaIref2Pmos = 4;
    */
};

#endif
