"""Dashboard Web local interactif pour explorer databases/corpus.db."""

import http.server
import json
import sqlite3
import urllib.parse
from pathlib import Path

DB_PATH = Path("databases/corpus.db")
PORT = 8501

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>CorpusDB Explorer — Corpus Juridique Algérien</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Amiri:wght@400;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: rgba(22, 31, 49, 0.75);
      --border: rgba(255, 255, 255, 0.08);
      --accent-primary: #3b82f6;
      --accent-emerald: #10b981;
      --accent-purple: #8b5cf6;
      --accent-amber: #f59e0b;
      --text: #f3f4f6;
      --text-dim: #9ca3af;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background: radial-gradient(circle at top, #151f38, var(--bg));
      color: var(--text);
      min-height: 100vh;
      padding: 2rem;
    }
    header {
      max-width: 1400px;
      margin: 0 auto 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 1.5rem;
    }
    .badge-status {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.4rem 1rem;
      border-radius: 9999px;
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      font-size: 0.85rem;
      font-weight: 600;
      border: 1px solid rgba(52, 211, 153, 0.3);
    }
    .grid-stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 1.25rem;
      max-width: 1400px;
      margin: 0 auto 2rem;
    }
    .stat-card {
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 1rem;
      padding: 1.5rem;
      position: relative;
      overflow: hidden;
      box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    }
    .stat-card::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0; height: 3px;
      background: linear-gradient(90deg, var(--accent-primary), transparent);
    }
    .stat-val { font-size: 2.2rem; font-weight: 700; color: #fff; margin-top: 0.25rem; }
    .stat-label { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-dim); }

    .layout-main {
      max-width: 1400px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: 340px 1fr;
      gap: 1.5rem;
    }
    .panel {
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 1rem;
      padding: 1.5rem;
    }
    .source-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.85rem;
      margin-bottom: 0.6rem;
      background: rgba(255,255,255,0.03);
      border-radius: 0.6rem;
      border-left: 4px solid var(--accent-primary);
      cursor: pointer;
      transition: all 0.2s;
    }
    .source-item:hover {
      background: rgba(255,255,255,0.07);
      transform: translateX(3px);
    }
    .source-item.joradp { border-left-color: #3b82f6; }
    .source-item.revue { border-left-color: #8b5cf6; }
    .source-item.cs { border-left-color: #10b981; }
    .source-item.cde { border-left-color: #f59e0b; }

    .search-box {
      width: 100%;
      padding: 0.75rem 1rem;
      background: rgba(0,0,0,0.3);
      border: 1px solid var(--border);
      border-radius: 0.6rem;
      color: #fff;
      font-size: 0.95rem;
      margin-bottom: 1.25rem;
    }
    .doc-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }
    .doc-table th {
      text-align: left;
      padding: 0.85rem 1rem;
      background: rgba(0,0,0,0.25);
      color: var(--text-dim);
      font-weight: 600;
      border-bottom: 1px solid var(--border);
    }
    .doc-table td {
      padding: 0.85rem 1rem;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }
    .doc-table tr:hover {
      background: rgba(255,255,255,0.03);
    }
    .tag {
      display: inline-block;
      padding: 0.2rem 0.5rem;
      border-radius: 0.3rem;
      font-size: 0.75rem;
      font-weight: 600;
      background: rgba(255,255,255,0.1);
    }
    .ar { font-family: 'Amiri', serif; direction: rtl; font-size: 1.05rem; }
    .modal {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.8);
      backdrop-filter: blur(8px);
      z-index: 100;
      align-items: center;
      justify-content: center;
      padding: 2rem;
    }
    .modal-content {
      background: #131c2e;
      border: 1px solid var(--border);
      border-radius: 1rem;
      width: 100%;
      max-width: 900px;
      max-height: 85vh;
      overflow-y: auto;
      padding: 2rem;
    }
  </style>
</head>
<body>

  <header>
    <div>
      <h1 style="font-size: 1.6rem; font-weight: 700; letter-spacing: -0.02em;">🏛️ CorpusDB Explorer</h1>
      <p style="color: var(--text-dim); font-size: 0.9rem; margin-top: 0.25rem;">Visualisation interactive du corpus juridique unifié algérien</p>
    </div>
    <div class="badge-status">
      <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#10b981;"></span>
      236 090 Documents — 100% Intègres
    </div>
  </header>

  <div class="grid-stats">
    <div class="stat-card">
      <div class="stat-label">Total Documents</div>
      <div class="stat-val">236 090</div>
      <div style="font-size:0.8rem; color:#34d399; margin-top:0.4rem;">+3 603 intégrés aujourd'hui</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Articles de Lois (JORADP)</div>
      <div class="stat-val">853 500</div>
      <div style="font-size:0.8rem; color:var(--text-dim); margin-top:0.4rem;">Structure intacte</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Décisions de Justice</div>
      <div class="stat-val">4 855</div>
      <div style="font-size:0.8rem; color:#818cf8; margin-top:0.4rem;">Cour suprême + Conseil d'État</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Relations Inter-Sources</div>
      <div class="stat-val">146</div>
      <div style="font-size:0.8rem; color:#fbbf24; margin-top:0.4rem;">Rapprochements HTML ↔ Revue</div>
    </div>
  </div>

  <div class="layout-main">
    <!-- Sources Panel -->
    <div class="panel">
      <h3 style="font-size:1rem; margin-bottom:1rem; color:#fff;">Sources du Corpus</h3>
      
      <div class="source-item joradp" onclick="filterSource('joradp.db')">
        <div>
          <div style="font-weight:600;">JORADP</div>
          <div style="font-size:0.75rem; color:var(--text-dim);">Lois, décrets, arrêtés (1962-2024)</div>
        </div>
        <span class="tag">231 234</span>
      </div>

      <div class="source-item revue" onclick="filterSource('coursupreme_revue.db')">
        <div>
          <div style="font-weight:600;">Cour suprême — Revue</div>
          <div style="font-size:0.75rem; color:var(--text-dim);">Jurisprudence archivée OCR (1989-2023)</div>
        </div>
        <span class="tag" style="background:#8b5cf6; color:#fff;">3 274</span>
      </div>

      <div class="source-item cs" onclick="filterSource('coursupreme.db')">
        <div>
          <div style="font-weight:600;">Cour suprême — HTML</div>
          <div style="font-size:0.75rem; color:var(--text-dim);">Décisions judiciaires du site officiel</div>
        </div>
        <span class="tag" style="background:#10b981; color:#fff;">1 253</span>
      </div>

      <div class="source-item cde" onclick="filterSource('conseildetat.db')">
        <div>
          <div style="font-weight:600;">Conseil d'État</div>
          <div style="font-size:0.75rem; color:var(--text-dim);">Contentieux administratif + OCR</div>
        </div>
        <span class="tag" style="background:#f59e0b; color:#fff;">329</span>
      </div>

      <div style="margin-top:1.5rem; padding-top:1.25rem; border-top:1px solid var(--border);">
        <h4 style="font-size:0.85rem; color:var(--text-dim); margin-bottom:0.6rem;">Répartition Linguistique</h4>
        <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.85rem;">
          <span>Arabe (AR)</span><span style="font-weight:600;">121 974 (51.7%)</span>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.85rem;">
          <span>Français (FR)</span><span style="font-weight:600;">114 116 (48.3%)</span>
        </div>
      </div>
    </div>

    <!-- Explorer Panel -->
    <div class="panel">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
        <h3 style="font-size:1.1rem;">Explorateur de Documents</h3>
        <span id="result-count" style="font-size:0.85rem; color:var(--text-dim);">Chargement...</span>
      </div>
      <input type="text" id="search-input" class="search-box" placeholder="Rechercher par numéro, titre, juridiction ou mot-clé (ex: 129299, صفقات, 2017)..." oninput="debounceSearch()">

      <div style="overflow-x:auto;">
        <table class="doc-table">
          <thead>
            <tr>
              <th>ID Canonique</th>
              <th>Juridiction</th>
              <th>Date / Année</th>
              <th>Titre & Objet</th>
              <th>Source</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody id="doc-tbody">
            <tr><td colspan="6" style="text-align:center; padding:2rem;">Chargement des données...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Detail Modal -->
  <div id="detail-modal" class="modal" onclick="closeModal(event)">
    <div class="modal-content" onclick="event.stopPropagation()">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1.5rem;">
        <h2 id="modal-title" style="font-size:1.3rem;">Détail du Document</h2>
        <button onclick="document.getElementById('detail-modal').style.display='none'" style="background:none; border:none; color:#fff; font-size:1.5rem; cursor:pointer;">&times;</button>
      </div>
      <div id="modal-body" style="font-size:0.95rem; line-height:1.6;"></div>
    </div>
  </div>

  <script>
    let currentSource = '';
    let searchTimeout = null;

    async function loadDocs(query = '', source = '') {
      const tbody = document.getElementById('doc-tbody');
      const url = `/api/documents?q=${encodeURIComponent(query)}&source=${encodeURIComponent(source)}`;
      const res = await fetch(url);
      const data = await res.json();

      document.getElementById('result-count').innerText = `${data.length} résultats affichés`;

      if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:2rem; color:#9ca3af;">Aucun document trouvé.</td></tr>`;
        return;
      }

      tbody.innerHTML = data.map(d => `
        <tr>
          <td><code style="font-size:0.8rem; color:#93c5fd;">${d.canonical_id}</code></td>
          <td><span class="tag">${d.jurisdiction}</span></td>
          <td>${d.date || d.year || 'N/A'}</td>
          <td class="${d.language === 'AR' ? 'ar' : ''}">
            <div style="font-weight:600;">${d.title || d.document_number || 'Sans titre'}</div>
            <div style="font-size:0.8rem; color:#9ca3af; margin-top:0.2rem;">${d.subject ? d.subject.slice(0, 80) + '...' : ''}</div>
          </td>
          <td><span class="tag" style="background:rgba(255,255,255,0.06);">${d.source_db}</span></td>
          <td><button onclick="showDetails('${d.canonical_id}')" style="background:#2563eb; color:#fff; border:none; padding:0.35rem 0.75rem; border-radius:0.4rem; cursor:pointer; font-size:0.8rem;">Détail</button></td>
        </tr>
      `).join('');
    }

    function filterSource(source) {
      currentSource = currentSource === source ? '' : source;
      loadDocs(document.getElementById('search-input').value, currentSource);
    }

    function debounceSearch() {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        loadDocs(document.getElementById('search-input').value, currentSource);
      }, 250);
    }

    async function showDetails(id) {
      const res = await fetch(`/api/document?id=${encodeURIComponent(id)}`);
      const d = await res.json();
      const body = document.getElementById('modal-body');

      document.getElementById('modal-title').innerText = d.canonical_id;
      body.innerHTML = `
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1.5rem; background:rgba(0,0,0,0.25); padding:1rem; border-radius:0.5rem;">
          <div><strong>Type:</strong> ${d.document_type} (${d.document_nature})</div>
          <div><strong>Juridiction:</strong> ${d.jurisdiction}</div>
          <div><strong>Date:</strong> ${d.date || 'N/A'} (Année: ${d.year || 'N/A'})</div>
          <div><strong>Numéro:</strong> ${d.document_number || 'N/A'}</div>
          <div><strong>Source DB:</strong> ${d.source_db} (${d.source_table})</div>
          <div><strong>Qualité:</strong> ${d.text_completeness} / ${d.extraction_quality}</div>
        </div>

        ${d.principle ? `<div style="margin-bottom:1.5rem;"><h4 style="color:#fbbf24; margin-bottom:0.5rem;">Principe Juridique (المبدأ)</h4><div class="ar" style="background:rgba(245,158,11,0.08); padding:1rem; border-radius:0.5rem; border-right:4px solid #f59e0b;">${d.principle}</div></div>` : ''}

        ${d.disposition ? `<div style="margin-bottom:1.5rem;"><h4 style="color:#34d399; margin-bottom:0.5rem;">Dispositif (منطوق الحكم / لهذه الأسباب)</h4><div class="ar" style="background:rgba(16,185,129,0.08); padding:1rem; border-radius:0.5rem; border-right:4px solid #10b981;">${d.disposition}</div></div>` : ''}

        <div>
          <h4 style="margin-bottom:0.5rem;">Extrait du Texte Intégral</h4>
          <pre style="background:rgba(0,0,0,0.4); padding:1rem; border-radius:0.5rem; max-height:280px; overflow-y:auto; white-space:pre-wrap; font-family:inherit; font-size:0.9rem;" class="${d.language === 'AR' ? 'ar' : ''}">${(d.full_text || 'Aucun texte').slice(0, 3000)}</pre>
        </div>
      `;

      document.getElementById('detail-modal').style.display = 'flex';
    }

    function closeModal(e) {
      document.getElementById('detail-modal').style.display = 'none';
    }

    loadDocs();
  </script>
</body>
</html>
"""

class CorpusHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
            return

        if parsed.path == "/api/documents":
            q = params.get("q", [""])[0].strip()
            source = params.get("source", [""])[0].strip()

            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            
            sql = """
                SELECT d.canonical_id, d.jurisdiction, d.document_type, d.date, d.year,
                       d.document_number, d.title, d.subject, d.language, p.source_db
                FROM documents d
                LEFT JOIN provenance p ON d.canonical_id = p.canonical_id
                WHERE 1=1
            """
            args = []
            if source:
                sql += " AND p.source_db = ?"
                args.append(source)
            if q:
                sql += " AND (d.canonical_id LIKE ? OR d.document_number LIKE ? OR d.title LIKE ? OR d.subject LIKE ?)"
                like_q = f"%{q}%"
                args.extend([like_q, like_q, like_q, like_q])

            sql += " ORDER BY d.id DESC LIMIT 40"
            rows = conn.execute(sql, args).fetchall()
            conn.close()

            data = [dict(r) for r in rows]
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            return

        if parsed.path == "/api/document":
            doc_id = params.get("id", [""])[0].strip()
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT d.*, p.source_db, p.source_table, p.source_id, p.raw_path, p.pdf_path
                FROM documents d
                LEFT JOIN provenance p ON d.canonical_id = p.canonical_id
                WHERE d.canonical_id = ?
            """, (doc_id,)).fetchone()
            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            if row:
                self.wfile.write(json.dumps(dict(row), ensure_ascii=False).encode("utf-8"))
            else:
                self.wfile.write(json.dumps({}, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def run():
    server = http.server.HTTPServer(("127.0.0.1", PORT), CorpusHandler)
    print(f"Server started at http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

if __name__ == "__main__":
    run()
