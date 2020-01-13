#include "Arduino.h"
/****************************************
Example Sound Level Sketch for the 
Adafruit Microphone Amplifier
****************************************/

/*
  Scheme 1:
  DAC0 : negative rail
  DAC1 : positive rail
  ADC0 : negative rail
  ADC1 : positive rail

 */
long duration;

#define ZERO 2037

#define KHZ 1000.0
#define MAXBUF 200
#define MAXSEQ 30
#define SEQTYPES 4
#define FORMS

const int TRIGGER_PIN = 12;    // Echo

//#define DAC_TO_VOLT (3.3/4096.0)
#define DAC_TO_VOLT (2.3/4096.0)
const float FREQ = 263184.21;
//74081.48 - 10 us (0.2814x)
//117658.82 - 5 us (0.447)
//181836.36 - 2 us (0.69x)
//222244.45 - 1 us (0.84x)
//263184.21 - 0 us
int N[SEQTYPES];
unsigned short DATA[SEQTYPES][MAXBUF];
unsigned char SEQ[MAXSEQ];
#define NANOMS 4
int ANOMS[NANOMS] = {15,16,17,18};
int M;
char FMTBUF[256];

void error(const char * msg){
  Serial.println(msg);
  exit(1);
}

float to_dac_val(float value){
  if(value < -1.0 || value > 1.0){
    error("value outside of range");
  }
  unsigned short val = ZERO + 1.0/DAC_TO_VOLT*(value);
  return val;
}

void set_anomalies(int seqno){
  for(int i=0; i < NANOMS; i += 1){
    SEQ[ANOMS[i]] = seqno;
  }
}
void clock(int seqno, float ampl, float freq_hz, float duty_cycle){
  float period = 1.0/freq_hz;
  int samples = period*FREQ + 1;
  int one_samples = duty_cycle*samples;
  int zero_samples = samples - one_samples;
  sprintf(FMTBUF, "period=%e samples=%d (%d,%d)",
          period, samples,one_samples,zero_samples);
  Serial.println(FMTBUF);
  if(samples > MAXBUF){
    error("too many samples");
  }
  int j = 0;
  for(int i=0; i < zero_samples/2; i+= 1){
    DATA[seqno][j] = to_dac_val(0.0);
    j += 1;
  }
  DATA[seqno][j] = to_dac_val(0.25*ampl); j++;
  DATA[seqno][j] = to_dac_val(0.50*ampl); j++;
  DATA[seqno][j] = to_dac_val(0.75*ampl); j++;
  for(int i=0; i < one_samples; i+= 1){
    DATA[seqno][j] = to_dac_val(ampl);
    j += 1;
  }
  DATA[seqno][j] = to_dac_val(0.75*ampl); j++;
  DATA[seqno][j] = to_dac_val(0.50*ampl); j++;
  DATA[seqno][j] = to_dac_val(0.25*ampl); j++;
  while(j < samples){
    DATA[seqno][j] = to_dac_val(0.0);
    j += 1;
  }
  N[seqno] = samples;
}

void noisy_wave(int seqno, float ampl, float freq_hz, float mean){
  float period = 1.0/freq_hz;
  int samples = period*FREQ+1;
  float omega = freq_hz/FREQ;
  sprintf(FMTBUF, "period=%e samples=%d", period, samples);
  Serial.println(FMTBUF);
  if(samples > MAXBUF){
    error("too many samples");
  }
  for(int i=0; i < samples; i += 1){
    float randval = (((float) random(256))-128.0)/128.0;
    float value = mean + randval*ampl;
    DATA[seqno][i] = to_dac_val(value);
    sprintf(FMTBUF,"value=%f code=%d",value,DATA[seqno][i]);
  }
  N[seqno] = samples;
}


void sin_wave(int seqno, float ampl, float freq_hz, float bias){
  float period = 1.0/freq_hz;
  int samples = period*FREQ+1;
  sprintf(FMTBUF, "period=%e samples=%d", period, samples);
  Serial.println(FMTBUF);
  if(samples > MAXBUF){
    error("too many samples");
  }
  float omega = (2.0*PI)/samples;
  for(int i=0; i < samples; i += 1){
    // sin in radians
    float value = ampl*sin(omega*i)+bias;
    DATA[seqno][i] = to_dac_val(value);
    sprintf(FMTBUF,"value=%f code=%d",value,DATA[seqno][i]);
  }
  N[seqno] = samples;
}


void set_zero(){
  for(int i=0; i < SEQTYPES; i += 1){
    for(int j=0; j < MAXBUF; j += 1){
      DATA[i][j] = ZERO;
    }
    N[i] = MAXBUF;
  }

  for(int i=0; i < MAXSEQ; i += 1){
    SEQ[i] = 0;
  }
}
void generate_signal(){
  int idx = 0;
  analogWrite(DAC0,ZERO);
  for(int i=0; i < MAXSEQ; i += 1){
    int seqno = SEQ[i];
    for(int j=0; j < N[seqno]; j += 1){
      analogWrite(DAC1, DATA[seqno][j]);
      idx += 1;
    }
  }
  sprintf(FMTBUF,"wrote %d values", idx);
  Serial.println(FMTBUF);
}

float get_time(){
  int total_samples = 0;
  for(int i=0; i < MAXSEQ; i += 1){
    int seqno = SEQ[i];
    total_samples += N[seqno];
  }
  float time = 1.0/FREQ*total_samples*1000.0;
  return time;
}
void set_signal(int type){
  set_zero();
  switch(type){
  case 'z':
    break;
  case 'a':
    sin_wave(0,0.1,40*KHZ,0.0);
    sin_wave(1,1.0,40*KHZ,0.0);
    set_anomalies(1);
    break;
  case 's':
    sin_wave(0,0.5,40*KHZ,0.0);
    break;
  case 'h':
    clock(0,1.0,2.5*KHZ,0.4);
    break;
  case 'i':
    clock(0,1.0,2.5*KHZ,0.4);
    clock(1,1.0,3.5*KHZ,0.8);
    set_anomalies(1);
    break;
  case 'b':
    // 6.08 KHZ
    sin_wave(0,0.5,40*KHZ,-0.5);
    sin_wave(1,0.5,40*KHZ,0.5);
    set_anomalies(1);
    break;
  case 'k':
    noisy_wave(0,0.2,40*KHZ,-0.8);
    noisy_wave(1,0.2,40*KHZ,0.8);
    set_anomalies(1);
    break;
  case 'f':
    sin_wave(0,1.0,40*KHZ,0.0);
    sin_wave(1,1.0,4*KHZ,0.0);
    set_anomalies(1);
    break;
  default:
    error("unsupported signal");
  }
  float time_ms = get_time();
  sprintf(FMTBUF, "signal_time=%f ms",time_ms);
  Serial.println(FMTBUF);
}
void setup()
{
   Serial.begin(115200);
   analogWriteResolution(12);
   set_zero();
   pinMode(TRIGGER_PIN, INPUT);
   attachInterrupt(digitalPinToInterrupt(TRIGGER_PIN),
                   generate_signal,
                   RISING);
}



void loop()
{
  char incomingByte;
  if (Serial.available() > 0) {
    // read the incoming byte:
    incomingByte = Serial.read();

    // say what you got:
    Serial.print("signal-code: ");
    Serial.println(incomingByte);
    set_signal(incomingByte);
  }
}
