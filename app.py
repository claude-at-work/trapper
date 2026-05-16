#!/usr/bin/env python3
import re
import subprocess
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

_ANSI = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def tmux(*args):
    result = subprocess.run(
        ['tmux'] + list(args),
        capture_output=True,
        text=True
    )
    return result.returncode == 0, result.stdout.strip(), result.stderr.strip()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/sessions')
def sessions():
    ok, out, _ = tmux('list-sessions', '-F', '#{session_name}')
    return jsonify([s for s in out.split('\n') if s] if ok else [])


@app.route('/api/windows')
def windows():
    session = request.args.get('session', '')
    if not session:
        return jsonify([])
    ok, out, _ = tmux(
        'list-windows', '-t', session, '-F',
        '#{window_index}:#{window_name}#{window_flags}'
    )
    return jsonify([w for w in out.split('\n') if w] if ok else [])


@app.route('/api/capture')
def capture():
    target = request.args.get('target', '')
    if not target:
        return jsonify({'ok': False, 'content': ''})
    ok, out, err = tmux('capture-pane', '-p', '-t', target)
    return jsonify({'ok': ok, 'content': _ANSI.sub('', out), 'error': err})


@app.route('/api/action', methods=['POST'])
def action():
    data = request.get_json()
    target = data.get('target', '')
    act = data.get('action', '')

    if not target or not act:
        return jsonify({'ok': False, 'error': 'Missing target or action'})

    session = target.split(':')[0]

    action_map = {
        'split-h':     ['split-window', '-h',  '-t', target],
        'split-v':     ['split-window', '-v',  '-t', target],
        'nav-left':    ['select-pane',  '-L',  '-t', target],
        'nav-right':   ['select-pane',  '-R',  '-t', target],
        'nav-up':      ['select-pane',  '-U',  '-t', target],
        'nav-down':    ['select-pane',  '-D',  '-t', target],
        'pane-zoom':   ['resize-pane',  '-Z',  '-t', target],
        'pane-kill':   ['kill-pane',          '-t', target],
        'win-new':     ['new-window',          '-t', session],
        'win-next':    ['next-window',         '-t', session],
        'win-prev':    ['previous-window',     '-t', session],
        'win-kill':    ['kill-window',         '-t', target],
        'copy-mode':   ['copy-mode',           '-t', target],
        'detach':      ['detach-client',       '-s', session],
        'new-session': ['new-session',   '-d', '-s', 'main'],
    }

    if act not in action_map:
        return jsonify({'ok': False, 'error': f'Unknown action: {act}'})

    ok, _, err = tmux(*action_map[act])
    return jsonify({'ok': ok, 'error': err})


@app.route('/api/send', methods=['POST'])
def send():
    data = request.get_json()
    target = data.get('target', '')
    keys = data.get('keys')
    text = data.get('text')
    enter = data.get('enter', False)

    if not target:
        return jsonify({'ok': False, 'error': 'Missing target'})

    if text is not None:
        ok, _, err = tmux('send-keys', '-l', '-t', target, text)
        if not ok:
            return jsonify({'ok': False, 'error': err})
        if enter:
            ok, _, err = tmux('send-keys', '-t', target, 'Enter')
        return jsonify({'ok': ok, 'error': err})

    if keys is not None:
        args = keys if isinstance(keys, list) else [keys]
        ok, _, err = tmux('send-keys', '-t', target, *args)
        return jsonify({'ok': ok, 'error': err})

    return jsonify({'ok': False, 'error': 'No keys or text provided'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
