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
    uint32_t clk;
    float n_samples;
    sprintf(FMTBUF,"runtime=%f buffer-size=%d\n",runtime,bufsiz);
    print_info(FMTBUF);
    do{
      ADC->ADC_MR &= ~ADC_MR_PRESCAL_Msk;
      ADC->ADC_MR |= ADC_MR_PRESCAL(presc);// set prescaler to fastest
      clk = adc_get_actual_adc_clock(ADC,SystemCoreClock);
      n_samples = runtime*clk;
      sprintf(FMTBUF,"  prescalar=%d clk=%d khz samps=%f\n", presc, clk/1000,n_samples);
      print_info(FMTBUF);
      presc += 1;
    } while(n_samples > bufsiz || clk > ADC_FREQ_MAX);
    return presc;
  }
  void track_adc_0(){
    ADC->ADC_COR = ADC_COR_DIFF1 | ADC_COR_DIFF0 | ADC_COR_OFF0 | ADC_COR_OFF1;
    ADC->ADC_CHER |= ADC_CHER_CH0 | ADC_CHER_CH1;
    // enable interrupt
    uint32_t interrupts = ADC_IER_EOC0;
    adc_disable_interrupt(ADC, ~interrupts);
    adc_enable_interrupt(ADC, interrupts);
  }
  void track_adc_6(){
    ADC->ADC_COR = ADC_COR_DIFF7 | ADC_COR_DIFF6 | ADC_COR_OFF6 | ADC_COR_OFF7;
    ADC->ADC_CHER |= ADC_CHER_CH6 | ADC_CHER_CH7;
    // enable interrupt
    uint32_t interrupts = ADC_IER_EOC6;
    adc_enable_interrupt(ADC, interrupts);
  }
  void setup(dma_info_t& info,
             float runtime,
             uint16_t * buf, uint32_t siz){
    dma::dma_info_t new_info;
    // Set up ADC
    print_info("configuring DMA\n");
    store_dma_state(info);
    summarize_dma_state(info);
    adc_stop(ADC);
    print_info("  -> reset data buffer\n");
    memset(buf,0,siz*sizeof(uint16_t));
    print_info("  -> configure adc sampler\n");
    ADC->ADC_MR |= ADC_MR_FREERUN_ON; // set free running mode on ADC
    ADC->ADC_MR &= ~ADC_MR_PRESCAL_Msk;
    int presc = find_prescalar(runtime,siz);
    ADC->ADC_MR |= ADC_MR_PRESCAL(presc);// set prescaler to fastest
    if(ADC->ADC_ISR & ADC_ISR_ENDRX){
    	print_info("post clock... buffer is populated?\n");
    }
    adc_enable_anch(ADC);
    track_adc_6();    

    print_info("  -> instantiated buffers\n");
    // configure the buffer to fill
    ADC->ADC_RPR = (uint32_t) buf;
    ADC->ADC_RCR = siz;

    print_info("  -> checking adc config\n");
    sprintf(FMTBUF, "min adc freq: %d\n", ADC_FREQ_MIN);
    print_info(FMTBUF);
    sprintf(FMTBUF, "max adc freq: %d\n", ADC_FREQ_MAX);
    print_info(FMTBUF);
    print_info("...done\n");
  }

  void run(){
    ADC->ADC_PTCR = ADC_PTCR_RXTEN;
    adc_start(ADC);
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
