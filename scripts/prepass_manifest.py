import os
import sys
import json
import re
from pathlib import Path

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff'}
TEXT_EXTENSIONS = {'.txt', '.md', '.markdown', '.org'}
CODE_EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.cpp', '.c', '.h', '.java', '.sh', '.bat', '.ps1', '.json', '.yaml', '.yml'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.aac'}
PDF_EXTENSIONS = {'.pdf'}

DOMAIN_KEYWORDS = {
    'ai_ml': ['backprop', 'gradient', 'loss', 'transformer', 'attention', 'neuron', 'weights', 'dataset', 'llm', 'inference', 'embedding', 'reinforcement', 'reward', 'stochastic'],
    'neurobiology': ['synapse', 'dopamine', 'hebbian', 'stdp', 'cortex', 'axon', 'neurotransmitter', 'plasticity', 'brain', 'membrane', 'action potential', 'нейрон', 'синапс', 'дофамин'],
    'networking': ['tcp', 'udp', 'vless', 'nginx', 'proxy', 'dns', 'ip', 'socket', 'http', 'tls', 'packet', 'routing', 'gateway', 'маршрут', 'протокол'],
    'systems_programming': ['memory', 'pointer', 'thread', 'concurrency', 'lock', 'mutex', 'cpu', 'cache', 'kernel', 'allocator', 'stack', 'heap'],
    'biology_medicine': ['atp', 'metabolism', 'glycolysis', 'enzyme', 'glucose', 'insulin', 'mitochondria', 'атф', 'метаболизм', 'глюкоза', 'фермент'],
    'strength_training': ['hypertrophy', '5x5', 'rm', 'rpe', 'periodization', 'cns fatigue', 'overload', 'силовые', 'гипертрофия', 'периодизация'],
    'philosophy_epistemology': ['epistemology', 'ontology', 'popper', 'dialectic', 'falsifiability', 'zettelkasten', 'luhmann', 'эпистемология', 'онтология', 'диалектика']
}

def detect_file_type(extension):
    ext = extension.lower()
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    if ext in TEXT_EXTENSIONS:
        return 'text'
    if ext in CODE_EXTENSIONS:
        return 'code'
    if ext in AUDIO_EXTENSIONS:
        return 'audio'
    if ext in PDF_EXTENSIONS:
        return 'pdf'
    return 'other'

def infer_domain_from_text(text):
    text_lower = text.lower()
    scores = {}
    for domain, kws in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in text_lower)
        if score > 0:
            scores[domain] = score
    if not scores:
        return None, 0.0
    sorted_domains = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_domain, best_count = sorted_domains[0]
    total_matches = sum(scores.values())
    confidence = round(best_count / total_matches, 2)
    return best_domain, confidence

def scan_inbox(target_dir, batch_size=8):
    path = Path(target_dir)
    if not path.exists():
        print(f"Error: Directory {target_dir} does not exist.")
        sys.exit(1)

    items = []
    file_stats = {'image': 0, 'text': 0, 'code': 0, 'audio': 0, 'pdf': 0, 'other': 0}

    for root, _, files in os.walk(path):
        for file in files:
            file_path = Path(root) / file
            ext = file_path.suffix
            ftype = detect_file_type(ext)
            file_stats[ftype] += 1

            size_bytes = file_path.stat().st_size
            sample_content = ""
            domain_guess = None
            confidence = 0.0

            if ftype in ('text', 'code') and size_bytes < 500000:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        sample_content = f.read(2000)
                    domain_guess, confidence = infer_domain_from_text(sample_content)
                except Exception:
                    pass

            item_info = {
                'relative_path': str(file_path.relative_to(path)).replace('\\', '/'),
                'file_name': file,
                'extension': ext,
                'type': ftype,
                'size_bytes': size_bytes,
                'domain_guess': domain_guess,
                'confidence': confidence,
                'preview': sample_content[:250].strip() if sample_content else None
            }
            items.append(item_info)

    batches = []
    for i in range(0, len(items), batch_size):
        batches.append(items[i:i + batch_size])

    ambiguous_items = [
        item for item in items 
        if item['type'] in ('text', 'code') and (item['domain_guess'] is None or item['confidence'] < 0.5)
    ]

    manifest = {
        'source_directory': str(path.resolve()),
        'total_files': len(items),
        'file_stats': file_stats,
        'batch_count': len(batches),
        'ambiguous_blocks_count': len(ambiguous_items),
        'ambiguous_samples': [
            {
                'file': item['file_name'],
                'preview': item['preview']
            } for item in ambiguous_items[:5]
        ],
        'batches': [
            {
                'batch_id': idx + 1,
                'files_count': len(b),
                'files': b
            } for idx, b in enumerate(batches)
        ]
    }

    output_file = path / 'manifest.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"Manifest created at: {output_file}")
    print(f"Total files: {len(items)}")
    print(f"File breakdown: {file_stats}")
    print(f"Ambiguous blocks requiring user disambiguation: {len(ambiguous_items)}")
    return manifest

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else '.'
    scan_inbox(target)
