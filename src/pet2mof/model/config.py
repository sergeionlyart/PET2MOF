"""Strict model-configuration provenance; unrelated legacy YAML is not model input."""
import math
from pathlib import Path
import yaml

TYPES = {'assumption_range', 'fit_on_C', 'unknown', 'literature_range', 'derived', 'regression_reference'}


def load_config(path):
    raw = yaml.safe_load(Path(path).read_text())
    def walk(node, where):
        if isinstance(node, dict):
            if 'value' in node or 'range' in node:
                required = ('unit', 'type', 'source_id', 'extraction_id', 'status')
                if any(not isinstance(node.get(k), str) or not node[k].strip() for k in required):
                    raise ValueError(f'{where}: number lacks provenance/unit/type/status')
                if node['type'] not in TYPES or ('value' in node) == ('range' in node):
                    raise ValueError(f'{where}: invalid parameter record')
                v = node.get('value', node.get('range'))
                if v is None:
                    if node['type'] != 'unknown':
                        raise ValueError(f'{where}: only unknown can have null value')
                    return None
                seq = v if isinstance(v, list) else [v]
                if not seq or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in seq):
                    raise ValueError(f'{where}: finite numeric value(s) required')
                if 'range' in node and (len(seq) != 2 or seq[0] > seq[1]):
                    raise ValueError(f'{where}: invalid interval')
                for k, extra in node.items():
                    if k not in ('value', 'range'):
                        walk(extra, f'{where}.{k}')
                return v
            return {k: walk(v, f'{where}.{k}') for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v, f'{where}[]') for v in node]
        if isinstance(node, (int, float, bool)):
            raise ValueError(f'{where}: bare number without provenance')
        return node
    return walk(raw, str(path))


def record(value, unit, *, source_id='DESIGN-T013', extraction_id='not_applicable',
           kind='assumption_range', status='debug', **extra):
    """Author choices are not data extractions; not_applicable is explicit."""
    return dict(value=value, unit=unit, type=kind, source_id=source_id,
                extraction_id=extraction_id, status=status, **extra)
