#include "AnalogLib.h"
#include "assert.h"
// y = -0.001592x + 3.267596
// R^2 = 0.999464
#ifdef _DUE

// for single-ended channels
#define ADC_CONVERSION (3300.0/4096.0)
// computed regression for ARDV -> OSCV: = 0.9888*V_ard - 0.0201
// R^2 = 0.99902
// ===== FULLSCALE =====
#define ADC_FULLSCALE (1208.0)
#define NORMALIZED_TO_CURRENT (2.0)

inline int from_diff_dma(int val){
  // convert to a single-ended differential value
  // with a resolution of 4096
  int new_val = -2*(val-2048);
  return new_val;
}
inline float to_diff_voltage(int val){
  //
  float val_mV = val*ADC_CONVERSION;
  return val_mV/1000.0;
}
inline float to_current(int val){
  //
  float val_mV = val*ADC_CONVERSION;
  float scaled_value = val_mV/ADC_FULLSCALE;
  float analog_current = NORMALIZED_TO_CURRENT*scaled_value;
  //return scaled_value;
  return analog_current;
}

int measure_seq_single(Fabric* fab,
                int ardAnaDiffChan,float* times, float* values, int& n){
  unsigned int pinmap[] = {7,6,5,4,3,2,1,0};
  unsigned int pos[SAMPLES];
  unsigned int neg[SAMPLES];
  unsigned int codes[SAMPLES];
  const unsigned int samples = SAMPLES;
  int i = 0;
  fab->cfgCommit();
  fab->execStart();
  for(unsigned int index = 0; index < SAMPLES; index++){
    pos[index] = analogRead(pinmap[ardAnaDiffChan+1]);
    neg[index] = analogRead(pinmap[ardAnaDiffChan]);
    codes[index] = micros();
  }
  fab->execStop();
  const float thresh = 1.0;
  assert(n <= SAMPLES);
  int oob_idx = n;
  for(unsigned int index = 0; index < n; index++){
    values[index] = to_current(pos[index] - neg[index]);
    times[index] = ((float)(codes[index]-codes[0]))*1.0e-6;
    if(index < oob_idx && fabs(values[index]) > thresh){
      oob_idx = index;
    }
  }
  return oob_idx;
}
int measure_seq_dma(Fabric* fab,
                int ardAnaDiffChan,float* times, float* values, int& n){
  unsigned int vals[SAMPLES];
  unsigned int codes[SAMPLES];
  const unsigned int samples = SAMPLES;
  int i = 0;
  fab->cfgCommit();
  fab->execStart();
  for(unsigned int index = 0; index < SAMPLES; index++){
    while ((ADC->ADC_ISR & 0x1000000) == 0);
    vals[index] = ADC->ADC_CDR[ardAnaDiffChan];
    codes[index] = micros();
  }
  fab->execStop();
  const float thresh = 1.0;
  assert(n <= SAMPLES);
  int oob_idx = n;
  for(unsigned int index = 0; index < n; index++){
    values[index] = to_current(from_diff_dma(vals[index]));
    times[index] = ((float)(codes[index]-codes[0]))*1.0e-6;
    if(index < oob_idx && fabs(values[index]) > thresh){
      oob_idx = index;
    }
  }
  return oob_idx;
}

float measure_dist_single(int ardAnaDiffChan, float& variance,int n){
  unsigned int pos[SAMPLES];
  unsigned int neg[SAMPLES];
  const unsigned int samples = n;
  unsigned int pinmap[] = {7,6,5,4,3,2,1,0};
  //                      {n,p,n,p,n,p,n,p}
  /*
    A0 A1 A2 A3 A4 A5 A6 A7
    P  N  P  N  P  N  P  N
    7  6  5  4  3  2  1  0
  */
  if(n > SAMPLES){
    error("measure_dist: not enough room in buffers to store values");
  }
  for(unsigned int index = 0; index < n; index++){
    pos[index] = analogRead(pinmap[ardAnaDiffChan+1]);
    neg[index] = analogRead(pinmap[ardAnaDiffChan]);
  }

  float values[SAMPLES];
  for(unsigned int index = 0; index < n; index++){
    values[index] = to_current(pos[index]-neg[index]);
    //sprintf(FMTBUF,"dist val=%d",val[index]);
    //print_info(FMTBUF);
  }
  float mean;
  util::distribution(values, SAMPLES, mean, variance);

  /*
  sprintf(FMTBUF,"chan=%d mean=%f var=%f", ardAnaDiffChan,
         mean,variance);
  print_info(FMTBUF);
  */
  return mean;
}

float measure_dist_dma(int ardAnaDiffChan, float& variance,int n){
  unsigned int vals[SAMPLES];
  const unsigned int samples = n;
  unsigned int pinmap[] = {7,6,5,4,3,2,1,0};
  //                      {n,p,n,p,n,p,n,p}
  /*
    A0 A1 A2 A3 A4 A5 A6 A7
    P  N  P  N  P  N  P  N
    7  6  5  4  3  2  1  0
  */
  if(n > SAMPLES){
    error("measure_dist: not enough room in buffers to store values");
  }
  for(unsigned int index = 0; index < n; index++){
    while ((ADC->ADC_ISR & 0x1000000) == 0);
    vals[index] = ADC->ADC_CDR[ardAnaDiffChan];

  }

  float values[SAMPLES];
  for(unsigned int index = 0; index < n; index++){
    values[index] = to_current(from_diff_dma(vals[index]));
    //sprintf(FMTBUF,"dist val=%d",val[index]);
    //print_info(FMTBUF);
  }
  float mean;
  util::distribution(values, SAMPLES, mean, variance);

  /*
  sprintf(FMTBUF,"chan=%d mean=%f var=%f", ardAnaDiffChan,
         mean,variance);
  print_info(FMTBUF);
  */
  return mean;
}




float measure_single(int ardAnaDiffChan, int n){
  unsigned long adcPos = 0;
  unsigned long adcNeg = 0;
  unsigned int pinmap[] = {7,6,5,4,3,2,1,0};
  float dummy;

  //                      {n,p,n,p,n,p,n,p}
  /*
    A0 A1 A2 A3 A4 A5 A6 A7
    P  N  P  N  P  N  P  N
    7  6  5  4  3  2  1  0
  */
  const unsigned int samples = n;
  for(unsigned int index = 0; index < samples; index++){
    adcPos += analogRead(pinmap[ardAnaDiffChan+1]);
    adcNeg += analogRead(pinmap[ardAnaDiffChan]);
  }
  float pos = (((float)adcPos)/samples);
  float neg = (((float)adcNeg)/samples);
  float value = to_current((int) (pos-neg));
  return value;
}

float measure_dma(int ardAnaDiffChan, int n){
  unsigned long adcVal = 0;
  unsigned int pinmap[] = {7,6,5,4,3,2,1,0};
  float dummy;

  //                      {n,p,n,p,n,p,n,p}
  /*
    A0 A1 A2 A3 A4 A5 A6 A7
    P  N  P  N  P  N  P  N
    7  6  5  4  3  2  1  0
  */
  const unsigned int samples = n;
  for(unsigned int index = 0; index < samples; index++){
    //adcPos += analogRead(pinmap[ardAnaDiffChan+1]);
    //adcNeg += analogRead(pinmap[ardAnaDiffChan]);
    while ((ADC->ADC_ISR & 0x1000000) == 0);
    adcVal += ADC->ADC_CDR[ardAnaDiffChan];
  }
  float digval = (((float)adcVal)/samples);
  //sprintf(FMTBUF,"meas val=%d",digval);
  //print_info(FMTBUF);
  float value = to_current(from_diff_dma((int) (digval)));
  return value;
}


int Fabric::Chip::Tile::Slice::ChipOutput::analogSeq(
                                                        float* times,
                                                        float* values,
                                                        int n
                                                        ) const {


  return measure_seq_single(this->getFabric(),ardAnaDiffChan,times,values,n);
}

void Fabric::Chip::Tile::Slice::ChipOutput::analogDist (
                                                        float& mean,
                                                        float& variance
                                                        ) const {


  mean = measure_dist_single(ardAnaDiffChan,variance,SAMPLES);
}


/*Measure the reading of an ADC from multiple samples*/
float Fabric::Chip::Tile::Slice::ChipOutput::fastAnalogAvg () const
{
  return measure_single(ardAnaDiffChan,100);
}
/*Measure the reading of an ADC from multiple samples*/
float Fabric::Chip::Tile::Slice::ChipOutput::analogAvg () const
{
  return measure_single(ardAnaDiffChan,SAMPLES);
}


float Fabric::Chip::Tile::Slice::ChipOutput::analogMax (int n) const
{
  error("unimplemented: analog max");
  return 0.0;
}
#endif
