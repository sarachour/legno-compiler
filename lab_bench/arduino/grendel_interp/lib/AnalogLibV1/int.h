#ifndef INTEG_H
#define INTEG_H

#include "fu.h"
#include "profile.h"
#include "calib_util.h"

typedef enum {
	mGainMRng = 0, /* -2 to 2  uA input, gain = 1,   -2 to 2  uA output*/
	mGainLRng = 1, /*-.2 to .2 uA input, gain = 1,  -.2 to .2 uA output*/
	mGainHRng = 2, /*-20 to 20 uA input, gain = 1,  -20 to 20 uA output*/
	hGainHRng = 3, /* -2 to 2  uA input, gain = 10, -20 to 20 uA output*/
	hGainMRng = 4, /*-.2 to .2 uA input, gain = 10,  -2 to 2  uA output*/
	lGainLRng = 5, /* -2 to 2  uA input, gain = .1, -.2 to .2 uA output*/
	lGainMRng = 6  /*-20 to 20 uA input, gain = .1,  -2 to 2  uA output*/
} intRange;

typedef struct {
  float eps;
  float k;
  float tc;
  float R2_eps;
  float R2_k;
} time_constant_stats;

typedef enum {
  OPENLOOP_TC,
  OPENLOOP_BIAS,
} open_loop_prop_t;

time_constant_stats estimate_time_constant(
                                           float k_value,
                                           int n,
                                           float * nom_times,float * nom_vals,
                                           float * k_times, float * k_vals);
time_constant_stats estimate_expo_time_constant(int n,
                                                float * nom_times,float * nom_vals);
class Fabric::Chip::Tile::Slice::Integrator : public Fabric::Chip::Tile::Slice::FunctionUnit {
	friend Slice;

	public:
		void setEnable ( bool enable ) override;
		void setInitialCode (
			unsigned char initialCode // fixed point representation of desired initial condition
			// 0 to 255 are valid
		);
    void setInitial(float initial);
		void setException (
			bool exception // turn on overflow detection
			// turning false overflow detection saves power if it is known to be unnecessary
		);
    void computeInterval(integ_state_t& state,
                         port_type_t port, float& min, float& max);

    static float computeInitCond(integ_state_t& m_codes);
    static float computeOutput(integ_state_t& m_codes,float input);
    static float computeTimeConstant(integ_state_t& m_codes);
    // z' = x - z

		bool getException() const;
    void setInv (bool inverse ); // whether output is negated
		void setRange (ifc port, range_t range);
    void update(integ_state_t codes);
    integ_state_t m_state;
		void calibrate (calib_objective_t obj);
		profile_t measure(profile_spec_t spec);
    void defaults();


	private:
		profile_t measureInitialCond(profile_spec_t spec);
		profile_t measureClosedLoopCircuit(profile_spec_t spec);
		profile_t measureOpenLoopCircuit(profile_spec_t spec);

    float calibrateHelper(Dac* ref_dac,
                         float* observations,
                         float * expected,
                         int & npts);

    void calibrateInitCond(calib_objective_t obj,
                           Dac * val_dac,
                           cutil::calib_table_t (&openloop_calib_table)[MAX_NMOS],
                           cutil::calib_table_t (&closedloop_calib_table)[MAX_NMOS]
                           );
  
  float getInitCondLoss(Dac * val_dac,calib_objective_t obj);
    float calibrateInitCondMinError(Dac * val_dac);
    float calibrateInitCondMaxDeltaFit(Dac * val_dac);
    void calibrateOpenLoopCircuit(calib_objective_t obj,
                                  Dac * val_dac,
                                  cutil::calib_table_t (&openloop_calib_table)[MAX_NMOS],
                                  cutil::calib_table_t (&closedloop_calib_table)[MAX_NMOS]
                                  );
    void calibrateClosedLoopCircuit(calib_objective_t obj,
                                    Fanout * fan,
                                    cutil::calib_table_t (&closedloop_calib_table)[MAX_NMOS]);

		Integrator (Slice * parentSlice);
		~Integrator () override { delete in0; delete out0; };
		/*Set enable, invert, range*/
		void setParam0 () const override;
		/*Set calIc, overflow enable*/
		void setParam1 () const override;
		/*Set initial condition*/
		void setParam2 () const override;
		/*Set calOutOs, calOutEn*/
		void setParam3 () const override;
		/*Set calInOs, calInEn*/
		void setParam4 () const override;
		void setParam5 () const override {};
		/*Helper function*/
		void setParamHelper (
			unsigned char selLine,
			unsigned char cfgTile
		) const;
		void setAnaIrefNmos () const override;
		void setAnaIrefPmos () const override;
		//const unsigned char anaIrefPmos = 5; /*5*/
		//unsigned char initialCode = 0; // fixed point representation of initial condition
		//bool exception = false; // turn on overflow detection
};

#endif
