"""Rebuild the typed graph dataset from versioned, cited curated inputs, offline."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

EDITION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EDITION))
from atlas.data import dataset, sources, valid_source
from atlas.graph import build_graph, validate_graph
from atlas.api import disease_bundle
from atlas.benchmark import report

def canonical(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')

def reproduce(output):
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output directory must be empty; existing files are never overwritten.')
    invalid = [s['id'] for s in sources().values() if not valid_source(s)]
    if invalid:
        raise ValueError('Source registry contract failed: ' + ', '.join(invalid))
    graphs = {d['id']: build_graph(d) for d in dataset()['diseases']}
    for graph in graphs.values():
        validate_graph(graph)
    output.mkdir(parents=True, exist_ok=True)
    files = {'curated_inputs.json': canonical(dataset()), 'sources.json': canonical(list(sources().values())),
             'benchmark.json': canonical(report())}
    for id, graph in graphs.items():
        files['graph-' + id + '.json'] = canonical(graph)
        bundle = disease_bundle(id)
        files['reasoning-' + id + '.json'] = canonical({k: bundle[k] for k in
            ('ranking', 'comparison', 'complementary', 'experiment')})
    for name, content in files.items():
        (output / name).write_bytes(content)
    manifest = dict(schema_version=1, source_snapshot=dataset()['retrieved_at'], source_count=len(sources()),
        literature_records=sum(bool(s.get('pmid')) for s in sources().values()),
        input_sha256=hashlib.sha256((EDITION / 'data/pilot_evidence.json').read_bytes()).hexdigest(),
        graphs={id: {'nodes': len(g['nodes']), 'edges': len(g['edges'])} for id, g in graphs.items()},
        output_sha256={name: hashlib.sha256(content).hexdigest() for name, content in files.items()},
        boundary='Reproduces the reviewed curated slice and its derived graph/reasoning, not autonomous literature discovery or a systematic review. No network/API/model calls.')
    (output / 'manifest.json').write_bytes(canonical(manifest))
    return manifest

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='New or empty output directory')
    args = parser.parse_args()
    try:
        manifest = reproduce(args.output)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps({'output': str(args.output.resolve()), 'sources': manifest['source_count'],
                      'literature_records': manifest['literature_records'], 'graphs': manifest['graphs']}, indent=2))
