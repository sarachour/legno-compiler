#include "AnalogLib.h"
#include "fu.h"
#include <float.h>
#include "assert.h"


char FMTBUF[64];

void Fabric::Chip::Tile::Slice::FunctionUnit::updateFu(){
  setAnaIrefNmos();
  setAnaIrefPmos();
  setParam0();
  setParam1();
  setParam2();
  setParam3();
  setParam4();
  setParam5();
}
