/*PIN ASSIGNMENTS*/
/*pins 0 - 1 are usb to host accessed through Serial*/

#define _DUE

/*INT, ADC PINS*/
/*CONTROL PINS*/
/*SPI PINS*/
const unsigned char ctrRstPin	 = 2; /*ctrRst*/
const unsigned char spiClkPin	 = 7; /*spi clk*/
const unsigned char spiMosiPin	 = 8; /*spi master out slave in*/
const unsigned char moMiEnPin	 = 13; /*moMiEn*/