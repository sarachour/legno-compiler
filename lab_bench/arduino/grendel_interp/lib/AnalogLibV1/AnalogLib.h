#include "Arduino.h"

#ifndef ANALOG_LIB1_API_H
#define ANALOG_LIB1_API_H

extern size_t dynamic_memory;

#define EMULATE


#define MAX_NMOS 8
#define MAX_PMOS 8
#define MAX_GAIN_CAL 64
#define MAX_BIAS_CAL 64


#define LEVEL 3

#define LOG_LEVEL 2
#define INFO_LEVEL 3
#define DEBUG_LEVEL 4

extern char FMTBUF[64];

#define NOMINAL_TIME_CONSTANT 126000.0
template <typename type>
void tally_dyn_mem(
	const char * name
) {
	dynamic_memory += sizeof(type);
	// Serial.print(sizeof(type));
	// Serial.print('\t');
	// Serial.println(name);
}


#define SAMPLES 200
#define FAST_SAMPLES 20
// how much to delay before measurement and how many times to measure

void print_log (const char * message);
void print_info (const char * message);
void print_debug (const char * message);
void error (const char * message);
void print_level(const char * message, int level);

#endif

#ifndef _PIN
#define _PIN
#include "pin.h"
#endif

#ifndef _FABRIC
#define _FABRIC
#include "fabric.h"
#endif

#ifndef _CHIP
#define _CHIP
#include "chip.h"
#endif

#ifndef _TILE
#define _TILE
#include "tile.h"
#endif

#ifndef _SLICE
#define _SLICE
#include "slice.h"
#endif

#include "fu.h"
#include "util.h"

#ifndef _CHIP_INOUT
#define _CHIP_INOUT
#include "chipInOut.h"
#endif

#ifndef _DAC
#define _DAC
#include "dac.h"
#endif

#ifndef _MUL
#define _MUL
#include "mul.h"
#endif

#ifndef _INT
#define _INT
#include "int.h"
#endif

#ifndef _FAN
#define _FAN
#include "fan.h"
#endif

#ifndef _ADC
#define _ADC
#include "adc.h"
#endif

#ifndef _LUT
#define _LUT
#include "lut.h"
#endif

#ifndef _TILE_INOUT
#define _TILE_INOUT
#include "tileInOut.h"
#endif

#ifndef _CONNECTION
#define _CONNECTION
#include "connection.h"
#endif

#ifndef _VECTOR
#define _VECTOR
#include "vector.h"
#endif

#ifndef _SPI
#define _SPI
#include "spi.h"
#endif

