"""C provenance, fixed fit weights, numerical identities and reproducible RNG."""
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import yaml
from pet2mof.model.config import load_config, record
from pet2mof.calibration.fit import loading, fit_s100, fit_carrier, verified_carriers
from pet2mof.calibration.metrics import aicc, metrics
from pet2mof.calibration.screening import draw, diagnostics

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('bad',[{'x':2.},{'x':{'value':2.,'unit':'bar'}},{'x':{'value':float('nan'),'unit':'bar','source_id':'s','extraction_id':'e','type':'fit_on_C','status':'debug'}}, {'x':{'value':2.,'range':[1.,3.],'unit':'bar','source_id':'s','extraction_id':'e','type':'fit_on_C','status':'debug'}}])
def test_configuration_rejects_unprovenanced_numbers(tmp_path,bad):
    p=tmp_path/'bad.yaml';p.write_text(yaml.safe_dump(bad))
    with pytest.raises(ValueError):load_config(p)


def test_all_model_configs_load():
    for name in ('calibration','scenarios','constants','demo_expected','fitted_debug'):
        assert load_config(ROOT/f'configs/{name}.yaml')


def test_two_loading_bases_and_S100_absolute_pressure():
    assert loading('30PEI@UiO-66','composite')==.3
    assert loading('30PEI@UiO-66','ratio')==pytest.approx(.3/1.3)
    from pet2mof.calibration.fit import load_s100
    f=load_s100(ROOT,'composite')
    assert np.allclose(f.p*100,f.x_display_kPa,rtol=1e-14)


def test_fit_uses_identical_covariance_and_preserves_failures():
    s=load_config(ROOT/'configs/calibration.yaml')['calibration']
    r=fit_s100(ROOT,s,profiles=False)
    assert r['models']['M1']['covariance']==r['models']['B1']['covariance']
    assert r['models']['M1']['AICc'] is None
    assert r['models']['M1']['metrics']['status']=='conditional_comparison'
    assert len(r['models']['M1']['predictions'])==39
    assert all(v['extraction_id']=='T006-S100-FigS5' for v in r['models']['M1']['predictions'])
    # Integration check: calibration's vectorised dry formula must equal the
    # public model, with the same provenance-bearing parameter mapping.
    from pet2mof.calibration.demo import make_models
    from pet2mof.model.gas import Gas
    from pet2mof.model.cycle import co2_total
    carriers=[dict(material='UiO-66',DOI='10.1021/acs.inorgchem.5b00435',gas=g,q_sat=2.,b=.1,Q=10000.,T_ref=298.) for g in ('Carbon Dioxide','Nitrogen')]
    scenario=load_config(ROOT/'configs/scenarios.yaml')['scenario']
    model,base=make_models(r,carriers,scenario)
    for name,m in [('M1',model),('B1',base)]:
        for point in r['models'][name]['predictions']:
            gas=Gas(298.,point['p_bar'],point['p_bar'],0.,0.)
            assert co2_total(m.equilibrium(point['w'],gas))==pytest.approx(point['q_predicted'],abs=1e-10)


def test_multitemperature_carrier_recovery_and_unknown_Q():
    rows=[]
    for T in (273.,298.,323.):
        for p in np.linspace(.01,1.,20):
            b=2.*np.exp(20000/8.31446261815324*(1/T-1/298))
            rows.append(dict(p_bar=p,T_K=T,q_mmol_g=5*b*p/(1+b*p),u_q=.02))
    f=pd.DataFrame(rows)
    r=fit_carrier(f)
    assert [r['q_sat'],r['b'],r['Q']]==pytest.approx([5.,2.,20000.],rel=1e-6)
    with pytest.raises(ValueError,match='multiple'):fit_carrier(f[f.T_K==298.])
    with pytest.raises(FileNotFoundError,match='verified'):verified_carriers(ROOT)


def test_error_metrics_do_not_upgrade_unknown_experimental_error():
    r=metrics([1.,2.],[1.01,1.99],[.1,.1],experimental_known=False)
    assert r['within_conditional_tolerances'] and r['status']=='conditional_comparison'
    assert aicc(1.,4,4) is None
    assert metrics([0.],[.01],[.1])['relative_errors']==[None]


def test_deterministic_seed_and_tied_optima():
    s=load_config(ROOT/'configs/scenarios.yaml')['scenario']
    x=np.random.Generator(np.random.PCG64(13013));y=np.random.Generator(np.random.PCG64(13013))
    assert [draw(x,s,'bicarbonate') for _ in range(3)]==[draw(y,s,'bicarbonate') for _ in range(3)]
    assert diagnostics([1.,2.,2.,1.],[0.,.1,.2,.3])['w_star']==[.1,.2]


def test_validation_missing_data_is_clear_and_no_read(tmp_path):
    import importlib.util
    spec=importlib.util.spec_from_file_location('validation',ROOT/'scripts/validate.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with pytest.raises(FileNotFoundError,match='V data unavailable'):module.validate(tmp_path)


def test_run_passport_command_has_no_machine_paths(tmp_path):
    from pet2mof.runs import _safe_command
    root = tmp_path / "repo"
    command = [str(tmp_path / "home" / "venv" / "bin" / "python3"), str(root / "scripts" / "demo.py"), "--flag"]
    assert _safe_command(command, root) == ["<external>/python3", "scripts/demo.py", "--flag"]
