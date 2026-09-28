import unittest

from opendbc.car.fw_versions import match_fw_to_car
from opendbc.car.honda.values import CAR
from opendbc.car.structs import CarParams


class TestCityFirmware(unittest.TestCase):
  # Recorded Honda response from the Brazilian City EXL 2025 incident.
  # No VIN, route identifier or forced vehicle selection is needed to reproduce it.
  OBSERVED_FW = b'8S102-T14-P020\x00\x00'
  ORIGINAL_FW = b'36161-T14-P050\x00\x00'

  def response(self, **overrides):
    fields = dict(ecu=CarParams.Ecu.fwdRadar, address=0x18dab0f1, responseAddress=0x18daf1b0,
                  subAddress=0, brand='honda', bus=0, logging=False, obdMultiplexing=True,
                  request=[b'\x22\xf1\x81'], fwVersion=self.OBSERVED_FW)
    fields.update(overrides)
    return CarParams.CarFw(**fields)

  def match(self, responses, **options):
    return match_fw_to_car(responses, '00000000000000000', log=False, **options)

  def test_observed_response_unique_exact_match(self):
    exact, candidates = self.match([self.response()])
    self.assertTrue(exact)
    self.assertEqual(candidates, {CAR.HONDA_CITY_7G})

  def test_original_response_still_matches(self):
    exact, candidates = self.match([self.response(fwVersion=self.ORIGINAL_FW)])
    self.assertTrue(exact)
    self.assertEqual(candidates, {CAR.HONDA_CITY_7G})

  def test_invalid_response_rejected(self):
    # Deliberately corrupted inputs, not additional vehicle firmware evidence.
    cases = [dict(fwVersion=b'8S102-T14-P021\x00\x00'), dict(fwVersion=self.OBSERVED_FW[:-1]),
             dict(fwVersion=b''), dict(address=0x18dab1f1), dict(subAddress=1),
             dict(brand='toyota'), dict(logging=True)]
    for changes in cases:
      with self.subTest(changes=changes):
        self.assertEqual(self.match([self.response(**changes)])[1], set())

  def test_no_responses_rejected(self):
    self.assertEqual(self.match([])[1], set())

  def test_conflicting_present_eps_rejected(self):
    # Missing EPS is allowed for this platform; a returned incompatible EPS must still reject it.
    incompatible_eps = CarParams.CarFw(ecu=CarParams.Ecu.eps, address=0x18da30f1,
                                      brand='honda', fwVersion=b'INVALID_TEST_ONLY')
    self.assertEqual(self.match([self.response(), incompatible_eps])[1], set())

  def test_single_response_does_not_enable_fuzzy_matching(self):
    self.assertEqual(self.match([self.response()], allow_exact=False)[1], set())


if __name__ == '__main__':
  unittest.main()
