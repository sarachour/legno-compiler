#include "AnalogLib.h"
#include <float.h>
#include "assert.h"
#include "calib_util.h"
#include "slice.h"
#include "dac.h"



profile_t Fabric::Chip::Tile::Slice::Dac::measure(profile_spec_t spec)
{
  if(!m_codes.enable){
    profile_t dummy;
    print_log("DAC not enabled");
    return dummy;
  }
  float scf = util::range_to_coeff(m_codes.range);
  cutil::calibrate_t calib;
  cutil::initialize(calib);

  int next_slice = (slice_to_int(parentSlice->sliceId) + 1) % 4;
  dac_code_t codes_dac = m_codes;
  m_codes = spec.code.dac;
  m_codes.source = DSRC_MEM;
  //setConstant(in);
  update(m_codes);

  cutil::buffer_dac_conns(calib,this);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,parentSlice->parentTile
                              ->parentChip->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);

	Connection dac_to_tile = Connection ( out0, parentSlice->tileOuts[3].in0 );
	Connection tile_to_chip = Connection ( parentSlice->tileOuts[3].out0,
                                         parentSlice->parentTile
                                         ->parentChip->tiles[3].slices[2].chipOutput->in0 );

  dac_to_tile.setConn();
	tile_to_chip.setConn();
  this->m_codes = spec.code.dac;
  float mean,variance;
  mean = this->fastMeasureValue(variance);
  sprintf(FMTBUF,"PARS mean=%f variance=%f",
          mean,variance);
  print_info(FMTBUF);
  const int mode = 0;
  const float in1 = 0.0;
  profile_t result = prof::make_profile(spec,
                                        mean,
                                        sqrt(variance));
  if(!calib.success){
    result.status = profile_status_t::FAILED_TO_CALIBRATE;
  }
	tile_to_chip.brkConn();
  dac_to_tile.brkConn();

  cutil::restore_conns(calib);
  update(codes_dac);
  return result;
}


