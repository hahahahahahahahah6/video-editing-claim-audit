"""Inspect documentation and Python syntax without executing project code."""
import ast
import os
import re
from pathlib import Path
from .phrases import VIDEOEDITING, NOVIDEOEDITING, GENERIC_NAMES


def normalize(text):
    return ' '.join(text.lower().replace('’', "'").replace("n't", ' not').replace('-', ' ').split())


def pattern(phrases):
    return re.compile(r'\b(?:' + '|'.join(re.escape(p) for p in sorted(phrases, key=lambda p: (-len(p), p))) + r')\b')


def paragraphs(text):
    lines, fence = [], None
    for line in text.splitlines():
        mark = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if fence:
            if re.match(r'^ {0,3}' + re.escape(fence[0]) + '{' + str(len(fence)) + r',}\s*$', line):
                fence = None
            lines.append('')
        elif mark:
            fence = mark.group(1)
            lines.append('')
        else:
            lines.append(line)
    return [normalize(p) for p in re.split(r'\n\s*\n', '\n'.join(lines)) if p.strip()]


def evidence(source):
    try:
        nodes = list(ast.walk(ast.parse(source)))
    except (SyntaxError, ValueError):
        return False
    imports, shadows, definitions = {}, set(), set()
    def names(target):
        if isinstance(target, ast.Name):
            return {target.id}
        if isinstance(target, (ast.Tuple, ast.List)):
            return set().union(*(names(x) for x in target.elts))
        if isinstance(target, ast.Starred):
            return names(target.value)
        return set()
    for node in nodes:
        if isinstance(node, ast.Import):
            for a in node.names:
                imports[a.asname or a.name.split('.')[0]] = a.name if a.asname else a.name.split('.')[0]
        elif isinstance(node, ast.ImportFrom) and not node.level:
            for a in node.names:
                imports[a.asname or a.name] = (node.module or '') + '.' + a.name
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.add(node.name)
            shadows.add(node.name)
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            targets = [x.optional_vars for x in node.items if x.optional_vars]
        for target in targets:
            shadows.update(names(target))
    clip = method = concat_video = ff_input = ff_edit = ff_end = False
    capture = read = writer = reader = image_writer = False
    methods = {'subclipped', 'with_section_cut_out', 'with_speed_scaled', 'cropped', 'resized', 'with_audio', 'with_effects_on_subclip'}
    filters = {'trim', 'atrim', 'concat', 'crop', 'scale', 'setpts'}
    extensions = ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.m4v', '.wmv', '.mpg', '.mpeg')
    for node in nodes:
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        resolved = ''
        if isinstance(func, ast.Name):
            if func.id not in shadows:
                resolved = imports.get(func.id, '')
            name = resolved.rsplit('.', 1)[-1]
        elif isinstance(func, ast.Attribute):
            name = func.attr
            base = func.value
            while isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name):
                if base.id in imports and base.id in shadows:
                    continue
                resolved = imports.get(base.id, '')
        else:
            continue
        if name in definitions:
            continue
        attr = isinstance(func, ast.Attribute)
        if name in GENERIC_NAMES and (attr or resolved):
            return True
        def library(lib, member, exact=None):
            return ((attr and name == member and (resolved == lib or resolved.startswith(lib + '.'))) or
                    (not attr and resolved in (exact or {lib + '.' + member})))
        clip |= library('moviepy', 'VideoFileClip')
        method |= attr and name in methods
        concat_video |= library('moviepy', 'concatenate_videoclips', {
            'moviepy.concatenate_videoclips',
            'moviepy.video.compositing.CompositeVideoClip.concatenate_videoclips',
            'moviepy.video.compositing.concatenate.concatenate_videoclips'})
        ff_input |= library('ffmpeg', 'input')
        ff_edit |= library('ffmpeg', 'concat')
        if attr and name == 'filter':
            values = ([node.args[0]] if node.args else []) + [k.value for k in node.keywords if k.arg == 'filter_name']
            ff_edit |= any(isinstance(v, ast.Constant) and isinstance(v.value, str) and v.value.lower() in filters for v in values)
        ff_end |= library('ffmpeg', 'output') or library('ffmpeg', 'run') or (attr and name == 'run')
        if library('cv2', 'VideoCapture') and node.args:
            arg = node.args[0]
            capture |= isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.lower().endswith(extensions)
        read |= attr and name == 'read'
        writer |= library('cv2', 'VideoWriter')
        reader |= library('imageio', 'get_reader', {'imageio.get_reader', 'imageio.v2.get_reader'})
        image_writer |= library('imageio', 'get_writer', {'imageio.get_writer', 'imageio.v2.get_writer'})
    return bool((clip and method) or concat_video or (ff_input and ff_edit and ff_end) or (capture and read and writer) or (reader and image_writer))



def audit(root, ignore=(), fail_on='high'):
    root = Path(root)
    if not root.is_dir() or not os.access(str(root), os.R_OK | os.X_OK):
        raise OSError('Not a readable directory: {}'.format(root))
    claims = denials = production = tests = False
    yes_re, no_re = pattern(VIDEOEDITING), pattern(NOVIDEOEDITING)
    for directory, dirs, files in os.walk(str(root), followlinks=False, onerror=lambda e: (_ for _ in ()).throw(e)):
        parent = Path(directory)
        def ignored(path):
            rel = path.relative_to(root).as_posix()
            return any(rel == p.rstrip('/') or rel.startswith(p.rstrip('/') + '/') for p in ignore)
        dirs[:] = sorted(d for d in dirs if not (parent / d).is_symlink() and not ignored(parent / d))
        for filename in sorted(files):
            path = parent / filename
            if path.is_symlink() or ignored(path):
                continue
            rel = path.relative_to(root)
            if (rel.as_posix() == 'README.md' or ('docs' in rel.parts and path.suffix == '.md')):
                for para in paragraphs(path.read_text(encoding='utf-8')):
                    denials |= bool(no_re.search(para))
                    claims |= bool(yes_re.search(no_re.sub(' ', para)))
            if path.suffix == '.py' and not any(x in rel.parts for x in ('fixtures', 'docs', 'examples')):
                is_test = 'tests' in rel.parts or filename.startswith('test_') or filename.endswith('_test.py')
                if evidence(path.read_text(encoding='utf-8')):
                    if is_test:
                        tests = True
                    else:
                        production = True
    findings = []
    if claims and not production:
        severity = 'MEDIUM' if tests else 'HIGH'
        findings.append({'rule': 'documented-video-editing-claim-false', 'severity': severity, 'message': 'Documented claim has ' + ('test-only evidence.' if tests else 'no production evidence.')})
    if denials and production:
        findings.append({'rule': 'documented-no-video-editing-claim-false', 'severity': 'HIGH', 'message': 'Documented denial conflicts with production evidence.'})
    fail = any(f['severity'] == 'HIGH' or fail_on.lower() == 'medium' for f in findings)
    return {'verdict': 'FAIL' if fail else 'PASS', 'findings': findings}
