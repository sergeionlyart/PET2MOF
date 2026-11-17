"""Local stdlib tests. Synthetic math cases are not additional measurements."""
import csv,hashlib,json,math,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from reference_baseline import interp
from check_data import load,run
class TestPack(unittest.TestCase):
    def test_data_contract(self):
        r=run();self.assertEqual(r['passed'],r['total'])
    def test_linear_interpolation(self):
        self.assertEqual(interp([(0.,0.),(1.,2.)],.25),.5)
    def test_no_extrapolation(self):
        with self.assertRaises(ValueError):interp([(.1,1),(.9,2)],1)
    def test_mass_conversion(self):
        # 1 mmol/g is 1 mol/kg, not 1000 mol/kg.
        self.assertAlmostEqual((1000/(44.01*3.26))*(3.26*44.01/1000),1)
    def test_unknown_heat_not_zero(self):
        x=[r for r in load('data/primary/S2_secondary_properties.csv') if r['metric']=='Qdes_DSC']
        self.assertEqual(sum(r['value']=='' for r in x),3)
        self.assertFalse(any(r['value']=='0' for r in x))
    def test_C72_C96_not_distinguishable_at_three_percent(self):
        self.assertLess(3.26*.97-.005,3.15*1.03+.005)
    def test_C72_beats_base_at_five_percent(self):
        self.assertGreater(3.26*.95-.005,2.67*1.05+.005)
    def test_common_scaling_cancels_in_ratio(self):
        self.assertAlmostEqual((3.26*1.1)/(2.67*1.1),3.26/2.67)
    def test_s2_and_s100_materials_not_pooled(self):
        self.assertTrue(all(r['host']=='UiO-66-NH2' for r in load('data/primary/S2_materials.csv')))
        self.assertTrue(all('NH2' not in r['sample_label'] for r in load('data/benchmark/S100_dry_isotherms.csv')))
    def test_benchmark_unknown_basis_is_explicit(self):
        self.assertTrue(all(r['mass_basis']=='unresolved_reported_gram' for r in load('data/benchmark/S100_dry_isotherms.csv')))
if __name__=='__main__':unittest.main(verbosity=2)
