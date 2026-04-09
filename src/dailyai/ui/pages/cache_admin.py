"""DailyAI hidden admin cache page.

Mobile-friendly operational view for cache health metrics and RSS Administration.
"""

from nicegui import ui, app

from dailyai.ui.components.theme import GLOBAL_CSS
from dailyai.api.routes import _get_admin_password
from dailyai.config import COUNTRIES
from dailyai.storage.backend import get_rss_feeds, save_rss_feed, delete_rss_feed

@ui.page('/_admin/cache')
async def cache_admin_page():
    ui.add_head_html(f'<style>{GLOBAL_CSS}</style>')
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1.0,'
        ' maximum-scale=1.0, user-scalable=no, viewport-fit=cover">'
    )
    ui.page_title('DailyAI Admin')
    ui.dark_mode(True)

    state = {'authenticated': False, 'token': ''}

    @ui.refreshable
    def admin_ui():
        if not state['authenticated']:
            with ui.column().classes('w-full max-w-sm mx-auto mt-20 p-6 bg-[var(--bg-card)] rounded-2xl border border-[var(--border-ghost)]'):
                ui.label('Admin Login').classes('text-2xl font-bold mb-2 text-[var(--text-primary)]')
                ui.label('Restricted access').classes('text-sm text-[var(--text-muted)] mb-6')
                
                pwd = ui.input('Password', password=True).classes('w-full mb-6').props('outlined')
                
                def try_login():
                    if pwd.value == _get_admin_password():
                        state['authenticated'] = True
                        state['token'] = pwd.value
                        admin_ui.refresh()
                    else:
                        ui.notify('Invalid password', color='negative')
                        
                ui.button('Login', on_click=try_login).classes('w-full').props('unelevated color=primary')
                pwd.on('keydown.enter', try_login)
            return

        with ui.column().classes('w-full max-w-[860px] mx-auto p-4'):
            with ui.row().classes('w-full justify-between items-center mb-4'):
                ui.label('DailyAI Admin').classes('text-2xl font-bold text-[var(--text-primary)]')
                
                def do_logout():
                    state['authenticated'] = False
                    state['token'] = ''
                    admin_ui.refresh()
                
                ui.button('Logout', on_click=do_logout).props('flat dense')

            with ui.tabs().classes('w-full') as tabs:
                cache_tab = ui.tab('Cache Health')
                rss_tab = ui.tab('RSS Feeds')
                
            with ui.tab_panels(tabs, value=cache_tab).classes('w-full bg-transparent p-0'):
                with ui.tab_panel(cache_tab):
                    render_cache_health(state['token'])
                with ui.tab_panel(rss_tab):
                    render_rss_admin(state['token'])

    admin_ui()


def render_rss_admin(token: str):
    container = ui.column().classes('w-full gap-4')
    
    country = None
    feed_key = None
    query = None

    async def toggle_feed(f, is_active):
        await save_rss_feed(f['country_code'], f['feed_key'], f['query'], is_active)
        ui.notify('Status updated')

    async def delete_feed(f):
        await delete_rss_feed(f['country_code'], f['feed_key'])
        ui.notify('Feed deleted')
        await load_feeds()

    async def add_feed():
        if not country.value or not feed_key.value or not query.value:
            ui.notify('All fields required', color='negative')
            return
        await save_rss_feed(country.value, feed_key.value, query.value, True)
        ui.notify(f'Added {feed_key.value}')
        feed_key.value = ''
        query.value = ''
        await load_feeds()

    async def seed_defaults():
        # First clear out existing ones or just run get_rss_feeds which will do it if empty, 
        # but to actually let them force-seed we can just insert directly.
        from dailyai.config import FEED_QUERIES, FEED_QUERIES_DE, FEED_QUERIES_GB, FEED_QUERIES_IN
        for key, q in FEED_QUERIES.items():
            await save_rss_feed("GLOBAL", key, q, True)
        for key, q in FEED_QUERIES_DE.items():
            await save_rss_feed("DE", key, q, True)
        for key, q in FEED_QUERIES_GB.items():
            await save_rss_feed("GB", key, q, True)
        for key, q in FEED_QUERIES_IN.items():
            await save_rss_feed("IN", key, q, True)
        ui.notify('Seeded default feeds from config')
        await load_feeds()

    async def load_feeds():
        container.clear()
        with container:
            feeds = await get_rss_feeds()
            if not feeds:
                ui.label('No custom RSS feeds configured.').classes('text-[var(--text-muted)] italic')
            else:
                for f in feeds:
                    with ui.card().classes('w-full bg-[var(--bg-card)] border-[var(--border-ghost)] p-3'):
                        with ui.row().classes('w-full justify-between items-center'):
                            with ui.column().classes('gap-0'):
                                ui.label(f"{f['country_code']} — {f['feed_key']}").classes('font-bold text-[var(--text-primary)] text-sm')
                                ui.label(f['query']).classes('text-xs text-[var(--text-secondary)] truncate max-w-[200px] sm:max-w-md')
                            with ui.row().classes('gap-2 items-center'):
                                ui.switch('Active', value=bool(f['is_active']), on_change=lambda e, curr=f: toggle_feed(curr, e.value)).props('dense')
                                ui.button(icon='delete', on_click=lambda curr=f: delete_feed(curr)).props('flat color=negative dense')

            with ui.card().classes('w-full mt-4 bg-[var(--bg-card)] border-[var(--border-ghost)] p-4'):
                with ui.row().classes('w-full justify-between items-center mb-2'):
                    ui.label('Add New Custom RSS').classes('font-bold text-lg text-[var(--text-primary)]')
                    ui.button('Seed Defaults from Config', on_click=seed_defaults).props('flat primary dense size=sm')
                
                with ui.row().classes('w-full gap-4 items-end'):
                    nonlocal country, feed_key, query
                    country = ui.select(options=list(COUNTRIES.keys()), value='GLOBAL', label='Country').classes('w-32').props('outlined dense')
                    feed_key = ui.input('Feed Key (e.g. techcrunch)').props('outlined dense').classes('flex-grow')
                    
                query = ui.input('RSS URL or query').props('outlined dense').classes('w-full mt-4')
                ui.button('Add Feed', on_click=add_feed).classes('mt-4').props('unelevated color=primary')

    ui.timer(0, load_feeds, once=True)


def render_cache_health(token: str):

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

    ui.run_javascript(f'''
    (function() {{
      if (window.__cacheHealthInit) return;
      window.__cacheHealthInit = true;

      function esc(text) {{
        return String(text)
          .replaceAll('&', '&amp;')
          .replaceAll('<', '&lt;')
          .replaceAll('>', '&gt;');
      }}

      function setText(id, value) {{
        const el = document.getElementById(id);
        if (el) el.textContent = value;
      }}

      function renderRows(containerId, rows) {{
        const el = document.getElementById(containerId);
        if (!el) return;
        if (!rows.length) {{
          el.innerHTML = '<div class="cache-row"><div class="cache-key">No data</div><div class="cache-val">-</div></div>';
          return;
        }}
        el.innerHTML = rows.join('');
      }}

      async function loadCacheHealth() {{
        try {{
          const res = await fetch('/api/admin/cache-health', {{ 
            headers: {{'Authorization': 'Bearer {token}'}},
            cache: 'no-store' 
          }});
          if (!res.ok) throw new Error('HTTP ' + res.status);
          const data = await res.json();

          setText('ch-limit', data.cache_limit ?? '-');
          setText('ch-total', data.total_articles ?? '-');
          setText('ch-keys', data.total_store_keys ?? '-');
          setText('ch-prune-runs', data?.prune?.runs ?? 0);
          setText('ch-prune-last-del', data?.prune?.last_deleted ?? 0);
          setText('ch-prune-total-del', data?.prune?.total_deleted ?? 0);
          setText('ch-prune-last-at', data?.prune?.last_at || '-');

          const keyRows = (data.per_store_key || []).map(function(item) {{
            return '<div class="cache-row">'
              + '<div class="cache-key">' + esc(item.store_key) + '</div>'
              + '<div class="cache-val">' + esc(item.article_count) + ' · max ' + esc(item.max_importance) + '</div>'
              + '</div>';
          }});
          renderRows('ch-store-keys', keyRows);

          const countryRows = Object.entries(data.per_country || {{}}).map(function(entry) {{
            return '<div class="cache-row">'
              + '<div class="cache-key">' + esc(entry[0]) + '</div>'
              + '<div class="cache-val">' + esc(entry[1]) + '</div>'
              + '</div>';
          }});
          renderRows('ch-country', countryRows);

          setText('ch-updated', 'Last updated: ' + new Date().toLocaleTimeString());
        }} catch (err) {{
          setText('ch-updated', 'Last updated: error · ' + err.message);
        }}
      }}

      loadCacheHealth();
      setInterval(loadCacheHealth, 30000);
    }})();
    ''')
