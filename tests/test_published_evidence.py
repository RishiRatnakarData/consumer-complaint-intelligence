"""Check that committed aggregate findings match their own immutable evidence snapshot.

These are consistency checks, NOT a substitute for retraining on live CFPB data.
"""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'docs' / 'evidence' / '2026-10-22'

def _load(name):
    return json.loads((PATH / name).read_text(encoding='utf-8'))

def test_snapshot_exists_and_is_non_row_level():
    assert (PATH / 'test_reliability.png').stat().st_size > 1000
    assert (PATH / 'calibrated_test_reliability.png').stat().st_size > 1000
    assert not any('predictions' in p.name.lower() or p.suffix == '.csv' for p in PATH.iterdir())

def test_research_split_counts_and_scope():
    report=_load('model_quality.json')
    research=_load('research_experiment.json')
    assert research['rows'] == 5000
    assert research['counts'] == report['split_counts']
    assert sum(research['counts'].values()) == research['rows']
    assert report['data_kind'] == 'cfpb_sample'
    assert 'has_narrative' in research['excluded_features']
    assert research['features'] == ['company','product','sub_product','issue','state','submitted_via']

def test_probabilities_and_holdout_denominators():
    report=_load('model_quality.json')
    n=report['split_counts']['test']
    for key in ('test_model','test_platt_calibrated','test_constant_baseline'):
        entry=report[key]
        assert entry['n']==n==1222
        assert sum(entry['confusion'].values())==n
        assert 0<=entry['roc_auc']<=1
        assert 0<=entry['brier_score']<=1
    assert report['test_platt_calibrated']['brier_score'] < report['test_model']['brier_score']
    assert report['test_model']['brier_score'] < report['test_constant_baseline']['brier_score']

def test_thresholds_are_not_mistaken_for_common_policy():
    r=_load('model_quality.json')
    assert r['threshold_source']=='validation'
    assert r['test_model']['threshold']==0.65
    assert r['test_platt_calibrated']['threshold']==0.5
    assert r['test_platt_calibrated']['recall'] < r['test_model']['recall']
