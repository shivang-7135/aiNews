"""DailyAI hidden admin cache page.

Mobile-friendly operational view for cache health metrics.
"""

from nicegui import ui

from dailyai.ui.components.theme import GLOBAL_CSS


@ui.page('/_admin/cache')
async def cache_admin_page():
    ui.add_head_html(f'<style>{GLOBAL_CSS}</style>')
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1.0,'
        ' maximum-scale=1.0, user-scalable=no, viewport-fit=cover">'
    )
    ui.page_title('DailyAI Admin — Cache Health')
    ui.dark_mode(True)

    ui.add_head_html('''
    <style>
      .cache-admin-wrap {
        max-width: 860px;
        margin: 0 auto;
        padding: 16px 14px 24px;
      }
      .cache-admin-title {
        font-size: 20px;
        font-weight: 800;
        color: var(--text-primary);
        margin-bottom: 4px;
      }
      .cache-admin-sub {
        font-size: 12px;
        color: var(--text-muted);
        margin-bottom: 14px;
      }
      .cache-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 8px;
      }
      .cache-stat {
        background: var(--bg-card);
        border: 1px solid var(--border-ghost);
        border-radius: 12px;
        padding: 10px;
      }
      .cache-stat-k {
        font-size: 11px;
        color: var(--text-muted);
      }
      .cache-stat-v {
        font-size: 18px;
        font-weight: 800;
        color: var(--text-primary);
        margin-top: 2px;
      }
      .cache-card {
        margin-top: 10px;
        background: var(--bg-card);
        border: 1px solid var(--border-ghost);
        border-radius: 12px;
        padding: 10px;
      }
      .cache-card h3 {
        font-size: 12px;
        font-weight: 700;
        color: var(--text-secondary);
        margin: 0 0 8px;
      }
      .cache-row {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        padding: 6px 0;
        border-top: 1px solid var(--border-ghost);
      }
      .cache-row:first-child { border-top: 0; }
      .cache-key {
        font-size: 12px;
        color: var(--text-primary);
        word-break: break-word;
      }
      .cache-val {
        font-size: 12px;
        color: var(--text-secondary);
        white-space: nowrap;
      }
      .cache-foot {
        margin-top: 10px;
        font-size: 11px;
        color: var(--text-muted);
      }
      @media (max-width: 640px) {
        .cache-grid { grid-template-columns: 1fr 1fr; }
      }
    </style>
    ''')

    ui.html('''
    <div class="cache-admin-wrap">
      <div class="cache-admin-title">Cache Health</div>
      <div class="cache-admin-sub">Hidden ops page · auto-refresh every 30s</div>

      <div class="cache-grid">
        <div class="cache-stat"><div class="cache-stat-k">Cache Limit</div><div class="cache-stat-v" id="ch-limit">-</div></div>
        <div class="cache-stat"><div class="cache-stat-k">Total Articles</div><div class="cache-stat-v" id="ch-total">-</div></div>
        <div class="cache-stat"><div class="cache-stat-k">Store Keys</div><div class="cache-stat-v" id="ch-keys">-</div></div>
        <div class="cache-stat"><div class="cache-stat-k">Prune Runs</div><div class="cache-stat-v" id="ch-prune-runs">-</div></div>
      </div>

      <div class="cache-card">
        <h3>Prune Stats</h3>
        <div class="cache-row"><div class="cache-key">Last Deleted</div><div class="cache-val" id="ch-prune-last-del">-</div></div>
        <div class="cache-row"><div class="cache-key">Total Deleted</div><div class="cache-val" id="ch-prune-total-del">-</div></div>
        <div class="cache-row"><div class="cache-key">Last Prune At</div><div class="cache-val" id="ch-prune-last-at">-</div></div>
      </div>

      <div class="cache-card">
        <h3>Per Store Key</h3>
        <div id="ch-store-keys"></div>
      </div>

      <div class="cache-card">
        <h3>Per Country</h3>
        <div id="ch-country"></div>
      </div>

      <div class="cache-foot" id="ch-updated">Last updated: -</div>
    </div>
    ''')

    ui.run_javascript('''
    (function() {
      if (window.__cacheHealthInit) return;
      window.__cacheHealthInit = true;

      function esc(text) {
        return String(text)
          .replaceAll('&', '&amp;')
          .replaceAll('<', '&lt;')
          .replaceAll('>', '&gt;');
      }

      function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
      }

      function renderRows(containerId, rows) {
        const el = document.getElementById(containerId);
        if (!el) return;
        if (!rows.length) {
          el.innerHTML = '<div class="cache-row"><div class="cache-key">No data</div><div class="cache-val">-</div></div>';
          return;
        }
        el.innerHTML = rows.join('');
      }

      async function loadCacheHealth() {
        try {
          const res = await fetch('/api/admin/cache-health', { cache: 'no-store' });
          if (!res.ok) throw new Error('HTTP ' + res.status);
          const data = await res.json();

          setText('ch-limit', data.cache_limit ?? '-');
          setText('ch-total', data.total_articles ?? '-');
          setText('ch-keys', data.total_store_keys ?? '-');
          setText('ch-prune-runs', data?.prune?.runs ?? 0);
          setText('ch-prune-last-del', data?.prune?.last_deleted ?? 0);
          setText('ch-prune-total-del', data?.prune?.total_deleted ?? 0);
          setText('ch-prune-last-at', data?.prune?.last_at || '-');

          const keyRows = (data.per_store_key || []).map(function(item) {
            return '<div class="cache-row">'
              + '<div class="cache-key">' + esc(item.store_key) + '</div>'
              + '<div class="cache-val">' + esc(item.article_count) + ' · max ' + esc(item.max_importance) + '</div>'
              + '</div>';
          });
          renderRows('ch-store-keys', keyRows);

          const countryRows = Object.entries(data.per_country || {}).map(function(entry) {
            return '<div class="cache-row">'
              + '<div class="cache-key">' + esc(entry[0]) + '</div>'
              + '<div class="cache-val">' + esc(entry[1]) + '</div>'
              + '</div>';
          });
          renderRows('ch-country', countryRows);

          setText('ch-updated', 'Last updated: ' + new Date().toLocaleTimeString());
        } catch (err) {
          setText('ch-updated', 'Last updated: error · ' + err.message);
        }
      }

      loadCacheHealth();
      setInterval(loadCacheHealth, 30000);
    })();
    ''')
