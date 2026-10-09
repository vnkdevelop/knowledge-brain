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

WIKILINK_PATTERN = re.compile(r'\[\[(.*?)\]\]')
YAML_FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)

def parse_yaml_simple(yaml_text):
    data = {}
    lines = yaml_text.strip().split('\n')
    current_key = None
    for line in lines:
        line_clean = line.strip()
        if not line_clean or line_clean.startswith('#'):
            continue
        if ':' in line and not line.startswith('-'):
            parts = line.split(':', 1)
            key = parts[0].strip()
            val = parts[1].strip()
            if val == '':
                data[key] = []
                current_key = key
            elif val.startswith('[') and val.endswith(']'):
                items = [x.strip().strip('"\'') for x in val[1:-1].split(',') if x.strip()]
                data[key] = items
                current_key = None
            else:
                data[key] = val.strip('"\'')
                current_key = None
        elif line.startswith('- ') and current_key:
            item = line[2:].strip().strip('"\'')
            if isinstance(data[current_key], list):
                data[current_key].append(item)
    return data

def index_vault(vault_dir):
    path = Path(vault_dir)
    if not path.exists():
        print(f"Error: Vault path {vault_dir} does not exist.")
        sys.exit(1)

    notes = {}
    mocs = {}
    seed_notes = []
    all_links = set()
    backlinks = {}

    for root, _, files in os.walk(path):
        for file in files:
            if not file.endswith('.md'):
                continue
            full_path = Path(root) / file
            rel_path = str(full_path.relative_to(path)).replace('\\', '/')

            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            fm_match = YAML_FRONTMATTER_PATTERN.match(content)
            metadata = {}
            body = content
            if fm_match:
                metadata = parse_yaml_simple(fm_match.group(1))
                body = content[fm_match.end():]

            note_title = metadata.get('title', file[:-3])
            note_type = metadata.get('type', 'concept')
            aliases = metadata.get('aliases', [])
            if isinstance(aliases, str):
                aliases = [aliases]
            tags = metadata.get('tags', [])
            if isinstance(tags, str):
                tags = [tags]

            links_found = [link.split('|')[0].strip() for link in WIKILINK_PATTERN.findall(body)]
            all_links.update(links_found)

            for target in links_found:
                if target not in backlinks:
                    backlinks[target] = []
                backlinks[target].append(note_title)

            is_seed = ('status/seed' in tags) or (metadata.get('status') == 'seed')
            if is_seed:
                seed_notes.append(note_title)

            note_entry = {
                'path': rel_path,
                'title': note_title,
                'type': note_type,
                'status': metadata.get('status', 'evergreen'),
                'aliases': aliases,
                'tags': tags,
                'outbound_links': links_found,
                'word_count': len(body.split())
            }

            if note_type == 'moc' or file.startswith('MOC - '):
                mocs[note_title] = note_entry
            else:
                notes[note_title] = note_entry

    for title, data in notes.items():
        data['inbound_links'] = backlinks.get(title, [])
    for title, data in mocs.items():
        data['inbound_links'] = backlinks.get(title, [])

    dead_links = [link for link in all_links if link not in notes and link not in mocs]

    index_result = {
        'vault_root': str(path.resolve()),
        'total_notes': len(notes),
        'total_mocs': len(mocs),
        'total_seeds': len(seed_notes),
        'dead_links_count': len(dead_links),
        'dead_links': sorted(list(set(dead_links))),
        'seed_notes': seed_notes,
        'mocs': mocs,
        'notes': notes
    }

    out_file = path / 'vault_index.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(index_result, f, ensure_ascii=False, indent=2)

    print(f"Vault successfully indexed!")
    print(f"Notes: {len(notes)} | MOCs: {len(mocs)} | Seeds: {len(seed_notes)} | Dead links: {len(dead_links)}")
    print(f"Index written to: {out_file}")
    return index_result

if __name__ == '__main__':
    v_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    index_vault(v_dir)
