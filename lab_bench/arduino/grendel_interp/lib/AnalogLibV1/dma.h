#ifndef DMA_H
#define DMA_H
#include <cstdint>
#include "AnalogLib.h"

namespace dma {

  typedef struct {
    uint32_t adc_mr;
    uint32_t adc_cor;
    uint32_t adc_cher;
    uint32_t adc_ier;
  } dma_info_t;

  void print_buffer(uint16_t* buf,uint32_t siz);
  void setup(dma_info_t& info,float sample_rate, uint16_t* buf, uint32_t siz);
  void run(Fabric* fab);
  void teardown(dma_info_t& info);
  void summarize_dma_state(dma_info_t& info);
  uint32_t get_frequency();
  void get_voltage_transform(float& scale, float& offset);
}

#endif
