#include "AnalogLib.h"
#include "fu.h"
#include <float.h>
#include "assert.h"

namespace util {

  /* validity testing */
  bool is_valid_iref(unsigned char code){
    return (code <= 7 && code >= 0);
  }

  void test_iref(unsigned char code){
    assert(is_valid_iref(code));
  }

  const char * ifc_to_string(ifc id){
    switch(id){
    case in0Id: return "x0"; break;
    case in1Id: return "x1"; break;
    case out0Id: return "z0"; break;
    case out1Id: return "z1"; break;
    case out2Id: return "z2"; break;
    default: return "?"; break;
    }
    return "?";
  }

  /* helper functions for building block functions */
  float sign_to_coeff(bool inv){
    return inv ? -1.0 : 1.0;
  }
  range_t range_to_dac_range(range_t rng){
    switch(rng){
    case RANGE_LOW:
      return RANGE_MED;
    case RANGE_MED:
      return RANGE_MED;
    case RANGE_HIGH:
      return RANGE_HIGH;
    }
    error("unknown range");
    return RANGE_UNKNOWN;
  }
  float range_to_coeff(range_t rng){
    switch(rng){
    case RANGE_LOW:
      return 0.1;
    case RANGE_MED:
      return 1.0;
    case RANGE_HIGH:
      return 10.0;
    }
    error("unknown range");
    return -1.0;
  }



  void distribution(float* values, int samples,
                     float& mean, float & variance){
    mean = 0.0;
    for(unsigned int index = 0; index < samples; index++){
      mean += values[index];
    }
    mean /= (float) samples;
    variance = 0.0;
    for(unsigned int index=0; index < samples; index++){
      variance += pow((values[index] - mean),2.0);
    }
    variance /= (float) (samples);
  }


  void linear_regression(float* times, float * values, int n,
                         float& alpha, float& beta ,float& Rsquare,
                         float& max_error,float& avg_error){
    float avg_time,avg_value,dummy;
    distribution(times,n,avg_time,dummy);
    distribution(values,n,avg_value,dummy);
    float slope_numer=0.0;
    float slope_denom=0.0;
    for(int i=0; i < n; i += 1){
      slope_numer += (times[i]-avg_time)*(values[i]-avg_value);
      slope_denom += (times[i]-avg_time)*(times[i]-avg_time);
    }
    alpha = slope_numer/slope_denom;
    beta = avg_value - alpha*avg_time;

    float SSRES = 0.0;
    float SSTOT = 0.0;
    avg_error = 0.0;
    max_error = 0.0;
    for(int i=0; i < n; i += 1){
      float pred = alpha*times[i]+beta;
      SSRES += pow(values[i]-pred,2);
      SSTOT += pow(values[i]-avg_value,2);
      float this_error = fabs(pred-values[i]);
      avg_error += this_error;
      max_error = max(max_error,this_error);
    }
    avg_error = avg_error/((float) n);
    Rsquare = 1.0 - SSRES/SSTOT;
  }
 int find_int_maximum(int* values, int n){
    int best_index=0;
    assert(n >= 1);
    for(int i=0; i < n; i+=1){
      if(values[i] > values[best_index]){
        best_index = i;
      }
    }
    return best_index;
  }
  int find_int_minimum(int* values, int n){
    int best_index=0;
    assert(n >= 1);
    for(int i=0; i < n; i+=1){
      if(values[i] < values[best_index]){
        best_index = i;
      }
    }
    return best_index;
  } 
  int find_maximum(float* values, int n){
    int best_index=0;
    assert(n >= 1);
    for(int i=0; i < n; i+=1){
      if(values[i] > values[best_index]){
        best_index = i;
      }
    }
    return best_index;
  }
  int find_minimum(float* values, int n){
    int best_index=0;
    assert(n >= 1);
    for(int i=0; i < n; i+=1){
      if(values[i] < values[best_index]){
        best_index = i;
      }
    }
    return best_index;
  }

  float find_best_gain_cal_linear(int * p, float * v, int n, int& point){
    float alpha,beta;
    int min_i = find_int_minimum(p,n);
    int max_i = find_int_maximum(p,n);
    alpha = (v[max_i]-v[min_i])/(p[max_i]-p[min_i]);
    beta = v[max_i] - alpha*p[max_i];
    sprintf(FMTBUF,"lin alpha=%f beta=%f",alpha,beta);
    print_info(FMTBUF);
    point = -1;
    float loss = 0.0;
    for(int i=0; i < MAX_GAIN_CAL; i += 1){
      float pred = alpha*i + beta;
      if(point < 0 || pred < loss){
        point = i;
        loss = pred; 
      }
    }
    return loss;
  }

  float find_best_gain_cal_poly(int * p, float * v, int n, int & point){
    double denom = (p[0] - p[1]) * (p[0] - p[2]) * (p[1] - p[2]);
    double A     = (p[2] * (v[1] - v[0]) + p[1] * (v[0] - v[2]) + p[0] * (v[2] - v[1])) / denom;
    double B     = (p[2]*p[2] * (v[0] - v[1]) + p[1]*p[1] * (v[2] - v[0]) + p[0]*p[0] * (v[1] - v[2])) / denom;
    double C     = (p[1] * p[2] * (p[1] - p[2]) * v[0] + p[2] * p[0] * (p[2] - p[0]) * v[1] + p[0] * p[1] * (p[0] - p[1]) * v[2]) / denom;
    // vertex form: y = a(x-h) + k
    // vertex is (h,k)
    int min_i = find_int_minimum(p,n);
    int max_i = find_int_maximum(p,n);
    float h = -B / (2*A);
    float k = C - B*B / (4*A);
    sprintf(FMTBUF,"poly a=%f b=%f c=%f vert=(%f,%f)",A,B,C,h,k);
    print_info(FMTBUF);
    point = -1;
    float loss = 0.0;
    for(int i=0; i < MAX_GAIN_CAL; i += 1){
      float pred = A*i*i + B*i + C;
      if(point < 0 || pred < loss){
        point = i;
        loss = pred; 
      }
    }
    return loss;
  }


  float find_best_gain_cal(int * p, float * v, int n, int & point){
    int min_i = find_int_minimum(p,n);
    int max_i = find_int_maximum(p,n);
    bool is_poly = false;
    for(int i=0; i < n; i+= 1){
      if(p[i] > p[min_i] && p[i] < p[max_i]){
        is_poly |= v[i] < v[min_i] && v[i] < v[max_i];
        is_poly |= v[i] > v[min_i] && v[i] > v[max_i];
      }
    }
    for(int i=0; i < n; i+=1){
      sprintf(FMTBUF,"%d\t%f", p[i],v[i]);
      print_info(FMTBUF);
    }
    float loss;
    if(is_poly)
      loss = find_best_gain_cal_poly(p,v,n,point);
    else
      loss = find_best_gain_cal_linear(p,v,n,point);
    sprintf(FMTBUF,"code=%d loss=%f",point,loss);
    print_info(FMTBUF);
    return loss;
  }
  void meas_dist_adc(Fabric::Chip::Tile::Slice::ChipAdc* fu,
                      float& mean, float& variance){
    Fabric* fab = fu->getFabric();
    fu->updateFu();
    fab->cfgCommit();
    float meas[SAMPLES];
    for(unsigned int i=0; i < SAMPLES; i += 1){
      meas[i] = (float) fu->getData();
    }
    distribution(meas, SAMPLES, mean, variance);
  }


  float meas_adc(Fabric::Chip::Tile::Slice::ChipAdc* fu){
    Fabric* fab = fu->getFabric();
    fu->updateFu();
    fab->cfgCommit();
    return fu->getData();
  }


  float meas_max_chip_out(Fabric::Chip::Tile::Slice::FunctionUnit* fu,int n){
    Fabric* fab = fu->getFabric();
    fu->updateFu();
    fab->cfgCommit();
    float value = fu->getChip()->tiles[3].slices[2].chipOutput
      ->analogMax(n);
    return value;
  }


  float meas_fast_chip_out(Fabric::Chip::Tile::Slice::FunctionUnit* fu){
    Fabric* fab = fu->getFabric();
    fu->updateFu();
    fab->cfgCommit();
    float value = fu->getChip()->tiles[3].slices[2].chipOutput
      ->fastAnalogAvg();
    return value;
  }



  float meas_chip_out(Fabric::Chip::Tile::Slice::FunctionUnit* fu){
    Fabric* fab = fu->getFabric();
    fu->updateFu();
    fab->cfgCommit();
    float value = fu->getChip()->tiles[3].slices[2].chipOutput
      ->analogAvg();
    return value;
  }


  void meas_dist_chip_out(Fabric::Chip::Tile::Slice::FunctionUnit* fu,
                     float& mean, float& variance){
    Fabric* fab = fu->getFabric();
    fu->updateFu();
    fab->cfgCommit();
    fu->getChip()->tiles[3].slices[2].chipOutput
      ->analogDist(mean,variance);
  }

  int meas_transient_chip_out(Fabric::Chip::Tile::Slice::FunctionUnit* fu,
                               float * times, float* values,
                               int samples){
    Fabric* fab = fu->getFabric();
    fu->updateFu();
    fab->cfgCommit();
    int n = fu->getChip()->tiles[3].slices[2].chipOutput
      ->analogSeq(times,values,samples);
    for(int i=0; i < n; i += 1){
      sprintf(FMTBUF," t=%f v=%f", times[i], values[i]);
      print_info(FMTBUF);
    }
    return n;
  }
  void meas_steady_chip_out(Fabric::Chip::Tile::Slice::FunctionUnit* fu,
                            float& mean, float& variance){
    Fabric* fab = fu->getFabric();
    fu->updateFu();
    fab->cfgCommit();
    fab->execStart();
    //wait for one millisecond.
    delay(3);
    fu->getChip()->tiles[3].slices[2].chipOutput
      ->analogDist(mean,variance);
    fab->execStop();
  }
}
