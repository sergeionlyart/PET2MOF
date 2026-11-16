#!/usr/bin/env python3
"""Offline T015 C fits, versioned comparison and diagnostic plots."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pet2mof.model.config import load_config, record
from pet2mof.calibration.revision import fit_revision, carrier_water_fits, make_revision_model
from pet2mof.model.cycle import periodic_cycle, heat
from pet2mof.model.gas import wet_gas, regeneration
from pet2mof.calibration.fit import fit_s100
from pet2mof.data.c_series import load_series
import yaml


def plots(root,result):
    out=root/'reports/T015'
    provenance='run_id: '+result['run_id']+'; C: T006-S100-FigS5'
    fig,axes=plt.subplots(2,2,figsize=(10,7),layout='constrained')
    original=result['v1_archived']['fits']
    for fit in original:
        for name,m in fit['models'].items():
            ax=axes[0 if fit['interpretation']=='composite' else 1,0 if name=='M1' else 1]
            for series in sorted({p['series'] for p in m['predictions']}):
                pts=[p for p in m['predictions'] if p['series']==series]
                ax.plot([p['p_bar'] for p in pts],[p['error'] for p in pts],'o-',label=series)
            ax.axhline(0,color='k',lw=.5);ax.set(title=f'archived v1 {name} {fit["interpretation"]}',xlabel='p CO2 (bar)',ylabel='prediction - observed (mmol/g reported basis)')
    axes[0,0].legend(fontsize=7);fig.suptitle(provenance,fontsize=8)
    fig.savefig(out/'diagnosis_residuals.png',dpi=150);plt.close(fig)
    f=load_series(root,sources=('S100',),roles=('C',),debug=True)
    f=f[f.status=='verified']
    host=f[f.material=='UiO-66']
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    shapes=[]
    for material,g in f.groupby('material'):
        if material=='UiO-66':continue
        p=g.p_bar.to_numpy(); q0=np.interp(p,host.p_bar,host.q_mmol_g)
        mask=(p>=host.p_bar.min())&(p<=host.p_bar.max())
        excess=g.q_mmol_g.to_numpy()-q0
        axes[0].plot(p[mask],excess[mask],'o-',label=material)
        # Per-curve ratios are a diagnostic transformation, never fitted parameters.
        axes[1].plot(p[mask],g.q_mmol_g.to_numpy()[mask]/q0[mask],'o-',label=material)
        shapes.append(dict(series=material,extraction_id='T006-S100-FigS5',p_bar=p[mask].tolist(),
            excess=excess[mask].tolist(),excess_slope=float(np.polyfit(p[mask],excess[mask],1)[0]),
            capacity_ratio=(g.q_mmol_g.to_numpy()[mask]/q0[mask]).tolist()))
    axes[0].set(xlabel='p CO2 (bar)',ylabel='q_w - interpolated q_0 (mmol/g reported basis)')
    axes[1].set(xlabel='p CO2 (bar)',ylabel='q_w / q_0');axes[0].legend(fontsize=7)
    fig.suptitle(provenance,fontsize=8);fig.savefig(out/'diagnosis_shapes.png',dpi=150);plt.close(fig)
    result['shape_diagnostics']=shapes
    for f in result['fits']:
        fig,axes=plt.subplots(2,2,figsize=(10,7),layout='constrained')
        for j,(name,m) in enumerate(f['models'].items()):
            for ci,sid in enumerate(sorted({p['series_id'] for p in m['predictions']})):
                pts=[p for p in m['predictions'] if p['series_id']==sid]
                p=[x['p_bar'] for x in pts];q=[x['q_observed'] for x in pts]
                color=f'C{ci}'
                axes[0,j].plot(p,q,'o',ms=3,color=color,label=sid.split('FigS5-')[1].split('-CO2')[0])
                axes[0,j].plot(p,[x['q_predicted'] for x in pts],'-',color=color)
                axes[1,j].plot(p,[x['error'] for x in pts],'o-',color=color)
                U=m['metrics']['series'][sid]['U']
                axes[1,j].fill_between(p,-np.array(U),U,color=color,alpha=.06)
            axes[0,j].set(title=name,ylabel='q (mmol/g reported basis)')
            axes[1,j].set(xlabel='p CO2 (bar)',ylabel='prediction - observed');axes[1,j].axhline(0,color='k',lw=.5)
        axes[0,0].legend(fontsize=6)
        fig.suptitle(f'{f["model_version"]} / {f["interpretation"]}\n'+provenance,fontsize=8)
        fig.savefig(out/f'{f["model_version"]}_{f["interpretation"]}.png',dpi=150);plt.close(fig)
        if f['models']['M1']['profiles']:
            profile=f['models']['M1']['profiles']['power']
            fig,ax=plt.subplots(figsize=(6,4),layout='constrained')
            ax.plot([r['fixed'] for r in profile],[r['delta_chi2'] for r in profile],'o-')
            ax.axhline(3.841,color='gray',ls='--',label='conditional LR reference (not full CI)')
            ax.set(xlabel='shared connectivity power',ylabel='profile chi2 - minimum',title=f['interpretation'])
            ax.legend(fontsize=7);fig.suptitle(provenance,fontsize=8)
            fig.savefig(out/f'profile_{f["interpretation"]}.png',dpi=150);plt.close(fig)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];out=root/'reports/T015';out.mkdir(parents=True,exist_ok=True)
    settings=load_config(root/'configs/calibration.yaml')['calibration']
    revision=load_config(root/'configs/revision.yaml')
    archived=json.loads((root/'reports/T013/demo.json').read_text())
    # Exact old fit implementation/weights remain executable; never overwrite v1.
    old=[fit_s100(root,settings,b,profiles=False) for b in ('composite','ratio')]
    for before,after in zip(archived['fits'],old):
        for name in ('M1','B1'):
            if abs(before['models'][name]['metrics']['RMSE']-after['models'][name]['metrics']['RMSE'])>1e-5:
                raise RuntimeError('archived v1 reproduction changed')
    result=dict(status='debug',run_id=args.run_id,model_version=revision['model_version'],
        scientific_status='C fit only; no independent validation; данных недостаточно',
        v1_archived=archived,v1_recomputed=old,
        fits=[fit_revision(root,settings,b,v) for v in revision['versions'] for b in ('composite','ratio')],
        c_fits=carrier_water_fits(root),dataset_ids=['T006-S100-FigS5','T011-S105-Fig8A','T011-S105-Fig8B','T011-S105-Fig8C','T011-S105-Fig9','T011-S106-Fig4'])
    scenario=load_config(root/'configs/scenarios.yaml')['scenario']
    selected=next(f for f in result['fits'] if f['model_version']==revision['model_version'] and f['interpretation']=='composite')
    model=make_revision_model(selected,result['c_fits'],scenario)
    result['nominal_cycle']=periodic_cycle(model,scenario['w'],wet_gas(**scenario['ads']),regeneration('R1'),tau_over_t=scenario['tau_over_t'])
    result['energy']=heat(result['nominal_cycle'],scenario['w'],scenario['ads']['T'],383.15)
    result['nominal_cycle_assumptions']=['all states per g dry composite', 'neutral chemistry',
        'S106 UiO-66_100 equivalent water volume and step transferred to S100; S105 CO2 Q/N2 transferred',
        'N2 Q=0 is lower endpoint of T013 stress range, not measured', 'Q_W=40000 J/mol is stress assumption',
        'prescribed-target finite time; no fitted CO2/H2O kinetics; heat remains unknown']
    plots(root,result)
    fitted={}
    for f in result['fits']:
        fitted[f['model_version']+'/'+f['interpretation']]={name:{k:record(v,'bar^-1' if k=='K_d' else '1',
              source_id='S100; DESIGN-T015',extraction_id='T006-S100-FigS5',kind='fit_on_C') for k,v in m['parameters'].items()}
              for name,m in f['models'].items()}
    (root/'configs/fitted_v1_1_debug.yaml').write_text(yaml.safe_dump(fitted,sort_keys=False))
    (out/'demo.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    for f in result['fits']:
        m=f['models']['M1']['metrics']
        print(f['model_version'],f['interpretation'],'RMSE',round(m['RMSE'],6),'all whole-series criteria',m['all_series_numerical_criteria'])

if __name__=='__main__':main()
