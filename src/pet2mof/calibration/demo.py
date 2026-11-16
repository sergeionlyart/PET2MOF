"""Offline S100 control reproduction and an explicitly conditional cycle."""
import json
from pathlib import Path
import yaml
from pet2mof.model.config import load_config, record
from pet2mof.model.isotherms import Isotherm, Site
from pet2mof.model.amines import Amines
from pet2mof.model.pores import Pores
from pet2mof.model.baseline import Baseline
from pet2mof.model.cycle import Model, periodic_cycle, heat
from pet2mof.model.gas import wet_gas, regeneration
from .fit import fit_s100, provisional_carriers


def make_models(fit, carriers, scenario):
    """Use S100 own CO2 at 298 K; temperature ratio from provisional C-PHYS.

    This is an explicit inter-batch transfer scenario, not final calibration.
    N2 parameters are never fabricated if the permitted carrier fit is missing.
    """
    candidates=[c for c in carriers if c['material']=='UiO-66' and c['DOI']=='10.1021/acs.inorgchem.5b00435']
    c=next(c for c in candidates if c['gas']=='Carbon Dioxide')
    n=next(c for c in candidates if c['gas']=='Nitrogen')
    co2=Isotherm((Site(fit['host']['q_sat'],fit['host']['b'],c['Q']),),fit['T_fit'])
    n2=Isotherm((Site(n['q_sat'],n['b'],n['Q']),),n['T_ref'])
    m,b=fit['models']['M1']['parameters'],fit['models']['B1']['parameters']
    pore=dict(scenario['pores'])
    pore['f_in']=m['kappa']*pore['rho_pei']*pore['V_p0']
    am=Amines(fit['n_N'],m['A0'],m['lam'],m['K_d'],Q_d=scenario['chemical_heat'],T_ref=fit['T_fit'])
    model=Model(co2,n2,Pores(**pore),am,scenario['water_step'])
    base=Model(co2,n2,None,None,{},baseline=Baseline(fit['n_N'],b['eta0'],b['K_d'],scenario['chemical_heat'],fit['T_fit']))
    return model,base


def write_fitted_config(results,path):
    raw={'description':'Debug fits; source interpretation and provenance retained; no frozen model yet.','fits':{}}
    for f in results:
        section={}
        values={'host_q_sat':(f['host']['q_sat'],'mmol/g MOF'),'host_b':(f['host']['b'],'bar^-1')}
        for name,model in f['models'].items():
            for key,value in model['parameters'].items():
                values[name+'_'+key]=(value,'bar^-1' if key=='K_d' else '1')
        for key,(value,unit) in values.items():
            section[key]=record(value,unit,source_id='S100; D-10; D-15',extraction_id='T006-S100-FigS5',kind='fit_on_C',status='debug')
        raw['fits'][f['interpretation']]=section
    Path(path).write_text(yaml.safe_dump(raw,sort_keys=False))


def reproduce(root, *, check_expected=True, profiles=True):
    root=Path(root)
    settings=load_config(root/'configs/calibration.yaml')['calibration']
    scenario=load_config(root/'configs/scenarios.yaml')['scenario']
    fits=[fit_s100(root,settings,kind,profiles=profiles) for kind in ('composite','ratio')]
    carriers=provisional_carriers(root)
    model,baseline=make_models(fits[0],carriers,scenario)
    ads=wet_gas(**scenario['ads']);des=regeneration('R1')
    cycle=periodic_cycle(model,scenario['w'],ads,des,tau_over_t=scenario['tau_over_t'],tolerance=scenario['cycle_tolerance'])
    base_cycle=periodic_cycle(baseline,scenario['w'],ads,des,tau_over_t=scenario['tau_over_t'],tolerance=scenario['cycle_tolerance'])
    result=dict(status='debug',fits=fits,carriers=carriers,cycle=cycle,baseline_cycle=base_cycle,
                energy=heat(cycle,scenario['w'],ads.T,des.T),
                dataset_ids=['T006-S100-FigS5']+[i['extraction_id'] for c in carriers for i in c['inputs']])
    scalars={'M1_composite_RMSE':fits[0]['models']['M1']['metrics']['RMSE'],
             'B1_composite_RMSE':fits[0]['models']['B1']['metrics']['RMSE'],
             'M1_ratio_RMSE':fits[1]['models']['M1']['metrics']['RMSE'],
             'B1_ratio_RMSE':fits[1]['models']['B1']['metrics']['RMSE'],
             'cycle_q_work':cycle['q_work'],'baseline_q_work':base_cycle['q_work']}
    result['regression_scalars']=scalars
    if check_expected:
        expected=load_config(root/'configs/demo_expected.yaml')
        for key,value in scalars.items():
            if abs(value-expected[key]['expected'])>expected[key]['atol']:
                raise RuntimeError(f'demo regression outside frozen debug tolerance: {key}')
    out=root/'reports/T013';out.mkdir(parents=True,exist_ok=True)
    (out/'demo.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    write_fitted_config(fits,root/'configs/fitted_debug.yaml')
    return result
