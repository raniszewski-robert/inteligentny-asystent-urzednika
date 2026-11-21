#!/usr/bin/env python3
"""Atrapa serwera LLM (API zgodne z OpenAI) do testów i demo kontroli halucynacji.

  python3 mock_llm.py 18081 good   # poprawne akapity
  python3 mock_llm.py 18082 bad    # akapity z wymyśloną kwotą 999 999 zł (draft.py ma je odrzucić)
Potem: LLM_BASE_URL=http://127.0.0.1:18082/v1 python3 draft.py ... --mode llm
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
MODE = sys.argv[2]
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        user = body['messages'][1]['content']
        n = user.count('<pytanie nr=')
        if MODE == 'good':
            paras = [{"no": i, "text": f"Ad {i}. Zgodnie z informacją wydziału: odpowiedź na pytanie {i}."} for i in range(1, n + 1)]
        else:  # halucynacja liczby
            paras = [{"no": i, "text": f"Ad {i}. Koszt wyniósł 999 999 zł."} for i in range(1, n + 1)]
        out = {"choices": [{"message": {"content": json.dumps({"paragraphs": paras}, ensure_ascii=False)}}]}
        self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers()
        self.wfile.write(json.dumps(out).encode())
    def log_message(self, *a): pass
HTTPServer(('127.0.0.1', int(sys.argv[1])), H).serve_forever()
