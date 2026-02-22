"""
PAPA Lang HTTP Server — route matching, request handler, start_server.
"""

import time
import json
from typing import Any, Dict, Optional, Tuple
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from .environment import Environment, ReturnSignal
from .stdlib_core import _to_json_value


def match_route(pattern: str, path: str) -> Optional[Dict[str, str]]:
    """Match route pattern like /users/:id against /users/123. Returns params or None."""
    pattern_parts = pattern.strip('/').split('/')
    path_parts = path.strip('/').split('/')
    if len(pattern_parts) != len(path_parts):
        return None
    params = {}
    for p, v in zip(pattern_parts, path_parts):
        if p.startswith(':'):
            params[p[1:]] = v
        elif p != v:
            return None
    return params


def create_http_handler(interp):
    """Create HTTP request handler class with access to interpreter."""
    routes_map = dict(interp.routes)

    class PapaHTTPHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] 🌐 {self.command} {self.path} -> {args[0] if args else ''}")

        def _send_cors(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

        def _send_json(self, data: Any, status: int = 200):
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors()
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)

        def _handle_route(self, method: str, path: str) -> Optional[Tuple[Any, int]]:
            parsed = urlparse(path)
            path_only = parsed.path or '/'

            for route_key, route_def in routes_map.items():
                rt_method, rt_pattern = route_key.split(' ', 1)
                if rt_method != method:
                    continue
                params = match_route(rt_pattern, path_only)
                if params is not None:
                    return (route_def, params)
            return None

        def do_OPTIONS(self):
            self.send_response(204)
            self._send_cors()
            self.end_headers()

        def do_GET(self):
            self._do_request('GET')

        def do_POST(self):
            self._do_request('POST')

        def do_PUT(self):
            self._do_request('PUT')

        def do_DELETE(self):
            self._do_request('DELETE')

        def _do_request(self, method: str):
            parsed = urlparse(self.path)
            path_only = parsed.path or '/'

            match = self._handle_route(method, path_only)
            if not match:
                self._send_json({'error': 'Not Found'}, 404)
                return

            route_def, params = match
            if route_def.auth_required:
                auth = self.headers.get('Authorization', '')
                if not auth or not auth.startswith('Bearer '):
                    self._send_json({'error': 'Unauthorized'}, 401)
                    return

            env = Environment(parent=interp.global_env)
            for k, v in params.items():
                env.set(k, v)

            if method in ('POST', 'PUT') and self.headers.get('Content-Length'):
                try:
                    length = int(self.headers.get('Content-Length', 0))
                    body_raw = self.rfile.read(length).decode('utf-8')
                    if body_raw.strip():
                        body_data = json.loads(body_raw)
                        body_papa = interp._py_to_papa(body_data)
                        env.set('body', body_papa)
                    else:
                        env.set('body', None)
                except Exception:
                    env.set('body', None)
            else:
                env.set('body', None)

            try:
                result = None
                try:
                    for stmt in route_def.body:
                        result = interp.execute(stmt, env)
                except ReturnSignal as ret:
                    result = ret.value
                out = _to_json_value(result)
                self._send_json(out)
            except Exception as e:
                self._send_json({'error': str(e)}, 500)

    return PapaHTTPHandler


def start_server(interp):
    """Start HTTP server with registered routes."""
    from .environment import PapaError

    if not interp.serve_config:
        raise PapaError("Сервер не настроен", hint="Добавьте 'serve on port N' в программу")
    port = interp.serve_config.port
    handler = create_http_handler(interp)
    server = HTTPServer(('', port), handler)
    print(f"\n🌐 Сервер запущен на http://localhost:{port}/")
    print("  Нажмите Ctrl+C для остановки\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Сервер остановлен")
        server.shutdown()


__all__ = ['match_route', 'create_http_handler', 'start_server']
