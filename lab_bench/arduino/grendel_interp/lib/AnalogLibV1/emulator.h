#ifndef EMULATOR_H
#define EMULATOR_H


#define GRID_SIZE 5
#include "block_state.h"

namespace emulator {

  // c0*i0 + c1*i1 + c2*f(i1,i2) + offset
  typedef struct {
    float mean;
    float std;
  } point_model_t;

  typedef struct {
    float min;
    float max;
  } bounds_model_t;

  typedef struct model {
    point_model_t error[GRID_SIZE][GRID_SIZE];
    bounds_model_t in0;
    bounds_model_t in1;
    bounds_model_t out;
  } physical_model_t;

  float draw(physical_model_t& phys_model, \
             float in0, float in1, float output, float & std);

  void bound(bounds_model_t& bnd,float min, float max);
  void ideal(physical_model_t& phys_model);
  void execute(physical_model_t phys_model,    \
                float in0, \
                float in1, \
                float& mean, \
                float& std);


}

#endif
