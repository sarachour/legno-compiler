#ifndef UTIL_H
#define UTIL_H

#include "AnalogLib.h"

typedef enum {
              MEAS_CHIP_OUTPUT,
              MEAS_CHIP_OUTPUT_DIST,
              MEAS_CHIP_OUTPUT_STEADY,
              MEAS_ADC
} meas_method_t;

namespace binsearch {
  bool find_bias_and_nmos(Fabric::Chip::Tile::Slice::FunctionUnit* fu,
                          float target,
                          const float max_error,
                          unsigned char & code,
                          unsigned char & nmos,
                          float & delta,
                          meas_method_t method
                          );
  float bin_search_meas(Fabric::Chip::Tile::Slice::FunctionUnit* fu,
                        meas_method_t method);

  void find_bias(Fabric::Chip::Tile::Slice::FunctionUnit* fu,
                 float target,
                 unsigned char & code,
                 float & error,
                 meas_method_t method);

  float get_bias(Fabric::Chip::Tile::Slice::FunctionUnit* fu,
                 float target,
                 meas_method_t method);
  void test_stab(unsigned char code,
                 float error,
                 const float max_error,
                 bool& calib_failed);
}

namespace util {

  const char * ifc_to_string(ifc id);

  // utilities for constructing compute functions
  float range_to_coeff(range_t range);
  range_t range_to_dac_range(range_t range);
  float sign_to_coeff(bool inv);

  // utilities for summarizing sequences o values
  void distribution(float * values, int size, float& mean, float& variance);
  float find_best_gain_cal(int * p, float * v, int n, int & point);
  int find_minimum(float * values, int size);
  int find_maximum(float * values, int size);
  void linear_regression(float* times, float * values, int n,
                         float& alpha, float& beta ,
                         float& Rsquare,
                         float& max_error,
                         float& avg_error);

  // utility for saving state
  void save_conns(Fabric::Chip::Tile::Slice::FunctionUnit* fu,
                  int& n,
                  int n_max);

  void meas_dist_adc(Fabric::Chip::Tile::Slice::ChipAdc* fu,
                          float& mean, float& variance);

  float meas_adc(Fabric::Chip::Tile::Slice::ChipAdc* fu);
  float meas_chip_out(Fabric::Chip::Tile::Slice::FunctionUnit* fu);
  float meas_fast_chip_out(Fabric::Chip::Tile::Slice::FunctionUnit* fu);
  float meas_max_chip_out(Fabric::Chip::Tile::Slice::FunctionUnit* fu,int n);

  void meas_dist_chip_out(Fabric::Chip::Tile::Slice::FunctionUnit* fu,
                          float& mean, float& variance);
  void meas_steady_chip_out(Fabric::Chip::Tile::Slice::FunctionUnit* fu,
                            float& mean, float& variance);
  int meas_transient_chip_out(Fabric::Chip::Tile::Slice::FunctionUnit* fu,
                               float * times, float * values,
                               int n_samples);
  void test_iref(unsigned char code);
  bool is_valid_iref(unsigned char code);

}

#endif
