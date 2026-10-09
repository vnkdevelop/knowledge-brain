import os
import sys
import re
from pathlib import Path

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

YAML_FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
WIKILINK_PATTERN = re.compile(r'\[\[(.*?)\]\]')
CALLOUT_PATTERN = re.compile(r'>\s*\[!([a-zA-Z0-9_\-]+)\]')

VALID_CALLOUTS = {
    'abstract', 'quote', 'ai-insight', 'synthesis', 'warning', 
    'fail', 'question', 'image-prompt', 'note', 'tip', 'important'
}

REQUIRED_FRONTMATTER_FIELDS = ['id', 'title', 'type', 'tags', 'created']

def validate_vault(vault_dir):
    path = Path(vault_dir)
    if not path.exists():
        print(f"Error: Vault path {vault_dir} does not exist.")
        sys.exit(1)

    errors = []
    warnings = []
    total_notes = 0

    all_titles = set()
    all_files = []

    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith('.md'):
                fpath = Path(root) / file
                all_files.append(fpath)
                all_titles.add(file[:-3])

    for fpath in all_files:
        total_notes += 1
        rel_path = str(fpath.relative_to(path)).replace('\\', '/')
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        fm_match = YAML_FRONTMATTER_PATTERN.match(content)
        if not fm_match:
            errors.append(f"[{rel_path}] Missing YAML Frontmatter block (--- ... ---)")
            continue

        fm_text = fm_match.group(1)
        for field in REQUIRED_FRONTMATTER_FIELDS:
            if f"{field}:" not in fm_text:
                errors.append(f"[{rel_path}] Missing required frontmatter field: '{field}'")

        body = content[fm_match.end():]
        words = body.split()
        if len(words) > 500 and not rel_path.startswith('MOC') and not rel_path.startswith('Dashboard'):
            warnings.append(f"[{rel_path}] Note exceeds 500 words limit ({len(words)} words) - consider atomization")

        callouts = CALLOUT_PATTERN.findall(body)
        for c in callouts:
            if c not in VALID_CALLOUTS:
                warnings.append(f"[{rel_path}] Unknown callout type: '[!{c}]'")

        links = WIKILINK_PATTERN.findall(body)
        for raw_link in links:
            target = raw_link.split('|')[0].strip()
            if target not in all_titles:
                warnings.append(f"[{rel_path}] Unresolved WikiLink: [[{target}]]")

    print("========================================")
    print("Knowledge Brain Vault Validation Report")
    print("========================================")
    print(f"Total markdown notes inspected: {total_notes}")
    print(f"Errors found: {len(errors)}")
    print(f"Warnings found: {len(warnings)}")
    print("----------------------------------------")

    if errors:
        print("\nERRORS (Must fix):")
        for err in errors[:20]:
            print(f"  [X] {err}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more errors")

    if warnings:
        print("\nWARNINGS (Recommendations):")
        for w in warnings[:20]:
            print(f"  [!] {w}")
        if len(warnings) > 20:
            print(f"  ... and {len(warnings) - 20} more warnings")

    if not errors and not warnings:
        print("\n[OK] Vault is 100% compliant with Knowledge Brain specification!")

    return len(errors) == 0

if __name__ == '__main__':
    v_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    success = validate_vault(v_dir)
    sys.exit(0 if success else 1)
