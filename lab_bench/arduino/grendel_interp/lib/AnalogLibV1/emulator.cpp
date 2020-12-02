#include "emulator.h"
#include "AnalogLib.h"
#include "stdlib.h"
#include "math.h"

namespace emulator {

  float _normal_dist(float mu, float std){
    float v1 = ((float) rand() + 1.)/(RAND_MAX+1.);
    float v2 = ((float) rand() + 1.)/(RAND_MAX+1.);
    float val = cos(2*3.14*v2)*sqrt(-2.0*log(v1));
    return val*std + mu;
  }

  float _normalize(bounds_model_t& bounds, float value){
    if(bounds.max - bounds.min < 1e-6){
      sprintf(FMTBUF, "bounds too small : (%f,%f)",bounds.min,bounds.max);
      error(FMTBUF);
    }

    float x = (value - bounds.min)/(bounds.max - bounds.min);
    return x;
  }
  float draw(physical_model_t& model, float in0, float in1, float out, float& std){
    float mean;
    std = 0.0;
    execute(model, in0, in1,  mean, std);
    sprintf(FMTBUF,"mean=%f std=%f in=(%f,%f) out=%f\n",mean,std,in0,in1,out);
    print_info(FMTBUF);
    return out + _normal_dist(mean,std);
  }

  void bound(bounds_model_t& bnd,float min, float max){
    bnd.min = min;
    bnd.max = max;
  }
  void ideal(physical_model_t& phys_model){
    for(int i=0; i < GRID_SIZE; i+=1){
      for(int j=0; j < GRID_SIZE; j+=1){
        phys_model.error[i][j].mean = 0.0;
        phys_model.error[i][j].std = 0.0;
      }
    }
  }

  float to_value(bounds_model_t bounds,int idx){
    return (bounds.max-bounds.min)/GRID_SIZE;
  }
  float _fact(int i){
    if(i == 1 || i == 0) return 1;
    else return _fact(i-1);
  }
  float _bernstein_poly(physical_model_t model, float u, int i){
    if(u < -1.0 || u > 1.0){
      sprintf(FMTBUF, "bernstein_poly: u=%f not normalized", u);
      error(FMTBUF);
    }
    float coeff = pow(u,i)*pow(1.0-u, GRID_SIZE - i);
    float nCi = _fact(GRID_SIZE)/(_fact(i)*_fact(GRID_SIZE-i));
    return nCi*coeff;

  }
  void execute(physical_model_t phys_model, float in0, float in1, float& mean, float& std){
    // u and v are between
    float BIs[GRID_SIZE];
    float BJs[GRID_SIZE];
    for(int i=0; i < GRID_SIZE; i+= 1){
      BIs[i] = _bernstein_poly(phys_model,
                               _normalize(phys_model.in0, in0), i);
    }
    for(int j =0; j < GRID_SIZE; j += 1){
      BJs[j] = _bernstein_poly(phys_model,
                               _normalize(phys_model.in1, in1), j);
    }
    mean = 0.0;
    std = 0.0;
    for(int i=0; i < GRID_SIZE; i+= 1){
      for(int j=0; j < GRID_SIZE; j += 1){
        point_model_t pt = phys_model.error[i][j];
        sprintf(FMTBUF,"(%d,%d) bi=%f bj=%f mean=%f std=%f\n", i,j,
                BIs[i],BJs[j],pt.mean,pt.std);
        print_info(FMTBUF);
        mean += BIs[i]*BJs[j]*pt.mean;
        std += BIs[i]*BJs[j]*pt.std;
      }
    }
  }

}
