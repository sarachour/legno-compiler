#include "dma.h"
#include "AnalogLib.h"
#include <cstdint>

namespace dma {

  void summarize_dma_state(dma_info_t& info){
    sprintf(FMTBUF,"ADC_MR=%lx\n", info.adc_mr);
    print_info(FMTBUF);
    sprintf(FMTBUF,"ADC_COR=%lx\n", info.adc_cor);
    print_info(FMTBUF);
    sprintf(FMTBUF,"ADC_CHER=%lx\n", info.adc_cher);
    print_info(FMTBUF);
    sprintf(FMTBUF,"ADC_IER=%lx\n", info.adc_ier);
    print_info(FMTBUF);

  }
  void store_dma_state(dma_info_t& info){
    info.adc_mr = ADC->ADC_MR;
    info.adc_cor = ADC->ADC_COR;
    info.adc_cher = ADC->ADC_CHER;
    info.adc_ier = ADC->ADC_IER;
  }

  void restore_dma_state(dma_info_t& info){
    ADC->ADC_MR = info.adc_mr;
    ADC->ADC_COR = info.adc_cor;
    ADC->ADC_CHER = info.adc_cher;
    ADC->ADC_IER = info.adc_ier;
    while ((ADC->ADC_ISR & 0x1000000) == 0);
  }

  uint32_t get_frequency(){
    return adc_get_actual_adc_clock(ADC,SystemCoreClock);
  }

  uint32_t find_prescalar(float runtime, uint32_t bufsiz){
    uint32_t presc = 0;
    float n_samples;
    sprintf(FMTBUF,"runtime=%f buffer-size=%d\n",runtime,bufsiz);
    print_info(FMTBUF);
    do{
      ADC->ADC_MR &= ~ADC_MR_PRESCAL_Msk;
      ADC->ADC_MR |= ADC_MR_PRESCAL(presc);// set prescaler to fastest
      uint32_t clk = adc_get_actual_adc_clock(ADC,SystemCoreClock);
      n_samples = runtime*clk;
      sprintf(FMTBUF,"  prescalar=%d clk=%d khz samps=%f\n", presc, clk/1000,n_samples);
      print_info(FMTBUF);
      presc += 1;
    } while(n_samples > bufsiz);
    return presc;
  }

  void setup(dma_info_t& info,
             float runtime,
             uint16_t * buf, uint32_t siz){
    dma::dma_info_t new_info;
    // Set up ADC
    print_info("configuring DMA\n");
    store_dma_state(info);
    summarize_dma_state(info);

    print_info("  -> reset data buffer\n");
    memset(buf,0,siz*sizeof(uint16_t));

    print_info("  -> configure adc sampler\n");
    ADC->ADC_MR |= ADC_MR_FREERUN_ON; // set free running mode on ADC
    //ADC->ADC_MR &= 0xFFFF00FF; // set prescaler to fastest
    ADC->ADC_MR &= ~ADC_MR_PRESCAL_Msk;
    int presc = find_prescalar(runtime,siz);
    ADC->ADC_MR |= ADC_MR_PRESCAL(presc);// set prescaler to fastest

    adc_enable_channel_differential_input(ADC, ADC_CHANNEL_0);
    //ADC->ADC_COR = 0x10000;  // enable differential ADC for all channels
    //ADC->ADC_COR = 0x00000; // single ended mode for all channels
    adc_enable_channel(ADC,ADC_CHANNEL_0);
    adc_enable_channel(ADC,ADC_CHANNEL_2);
    adc_enable_channel(ADC,ADC_CHANNEL_4);
    adc_enable_channel(ADC,ADC_CHANNEL_6);

    // enable interrupt
    uint32_t interrupts = ADC_IER_DRDY | ADC_IER_EOC0 | ADC_IER_EOC2
      | ADC_IER_EOC4 | ADC_IER_EOC6;
    adc_enable_interrupt(ADC, interrupts);
    store_dma_state(new_info);
    summarize_dma_state(new_info);
 
    print_info("  -> instantiated buffers\n");
    // configure the buffer to fill
    ADC->ADC_RPR = (uint32_t) buf;
    ADC->ADC_RCR = siz;
    ADC->ADC_PTCR = ADC_PTCR_RXTEN;
    //
    while ((adc_get_status(ADC) & ADC_ISR_DRDY) == 0);

    print_info("...done\n");
  }

  void run(){
    ADC->ADC_CR |= ADC_CR_START;
    while(!(ADC->ADC_ISR & ADC_ISR_ENDRX)){
      delay(1);
    }
  }

  void get_voltage_transform(float& scale, float& offset){
    scale = 2.0/2048;
    offset = -1.0;
  }
  inline float dma_val_to_voltage(uint16_t val){
    return 2.0*(val-2048)/2048;
  }
  void print_buffer(uint16_t* buf,uint32_t siz){
    for(int i=0; i < siz; i+=1){
      float val = dma_val_to_voltage(buf[i]);
      sprintf(FMTBUF, "idx=%d code=%d val=%f\n",i,buf[i],val);
      print_info(FMTBUF);
    }
  }
  void teardown(dma_info_t& info){
    print_info("tearing down!\n");
    restore_dma_state(info);
  }


}
