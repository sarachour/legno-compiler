#include "AnalogLib.h"

size_t dynamic_memory = 0;

Fabric::Fabric () {

	/*USB connection to PC*/
	Serial.begin(115200);
	/*SET PIN DIRECTIONS*/
	/*CONTROL PINS*/
	/*SPI PINS*/
	pinMode(ctrRstPin, OUTPUT);
	pinMode(spiClkPin, OUTPUT);
	pinMode(spiMosiPin, OUTPUT);
	pinMode(moMiEnPin, OUTPUT);

	/*ANALOG INPUT CHANNEL ENABLE PINS*/
	pinMode(26, OUTPUT);
	pinMode(27, OUTPUT);
	pinMode(28, OUTPUT);
	pinMode(29, OUTPUT);

	digitalWrite(moMiEnPin, LOW); /*scan chain disable*/

	/*ANALOG PINS*/
	#ifdef _DUE
		analogReadResolution(12);
		analogWriteResolution(12);
	#else
		analogReference(DEFAULT);
	#endif

	/*random addr seed*/
	randomSeed(analogRead(0));

	// Set up ADC
	//ADC->ADC_MR |= 0x80; // set free running mode on ADC
	//ADC->ADC_MR &= 0xFFFF00FF; // set prescaler to fastest
  	//ADC->ADC_COR = 0x10000;  // enable differential ADC for all channels
  	//ADC->ADC_COR = 0x00000; // single ended mode for all channels
	//ADC->ADC_CHER = 0x55; // enable four pairs of differential ADC
	//adc_enable_interrupt(ADC, ADC_IER_DRDY);
	//ADC->ADC_IER |= 0x55; // enable ADC interrupt on pin A0
	//while ((ADC->ADC_ISR & 0x1000000) == 0);

	Serial.println("initialized arduino");

	#ifdef _DUE
		// Serial.println("fast reset");
		digitalWriteDirect(ctrRstPin, HIGH);
		digitalWriteDirect(ctrRstPin, LOW);
	#else
		// Serial.println("regular reset");
		digitalWrite(ctrRstPin, HIGH);
		digitalWrite(ctrRstPin, LOW);
	#endif

	/*create chips*/
	chips = new Chip[2] {
		Chip (this, chipRow0, chipCol0, 30, 25, 24, 3, 9, 4),
		Chip (this, chipRow0, chipCol1, 31, 23, 22, 50, 14, 0)
	};
	tally_dyn_mem <Chip[2]> ("Chip[2]");

	print_info("allocated hcdc");
	cfgCommit();

	print_info("initialized hcdc");
}

Fabric::~Fabric() { 
	Serial.println("Fabric dtor");
	delete[] chips;
};

void Fabric::defaults() {
  chips[0].defaults();
  chips[1].defaults();
}
void Fabric::reset () {
	Serial.begin(115200);
	digitalWrite(moMiEnPin, LOW); /*scan chain disable*/
	print_info("initialized arduino");

	#ifdef _DUE
		// Serial.println("fast reset");
		digitalWriteDirect(ctrRstPin, HIGH);
		digitalWriteDirect(ctrRstPin, LOW);
	#else
		// Serial.println("regular reset");
		digitalWrite(ctrRstPin, HIGH);
		digitalWrite(ctrRstPin, LOW);
	#endif

	/*create chips*/
	delete[] chips;
	chips = new Chip[2] {
		Chip (this, chipRow0, chipCol0, 30, 25, 24, 3, 9, 4),
		Chip (this, chipRow0, chipCol1, 31, 23, 22, 50, 14, 0)
	};
	tally_dyn_mem <Chip[2]> ("Chip[2]");


	cfgCommit();

	print_info("initialized fabric");
}

