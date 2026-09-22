/* Concierge overlay.
 *
 * The transcript lives here in the browser and is posted back whole with each
 * turn: there is no database on this site, and the server keeps no session.
 */
(function () {
  var OPEN_LABEL = 'Plan & book';

  var dock = document.getElementById('concierge-dock');
  var toggleBtn = document.getElementById('concierge-toggle');
  var toggleLabel = toggleBtn && toggleBtn.querySelector('.concierge-handle-label');
  var toggleIcon = toggleBtn && toggleBtn.querySelector('.concierge-handle-icon');
  var panel = document.getElementById('concierge-panel');
  var form = document.getElementById('concierge-form');
  var input = document.getElementById('concierge-input');
  var sendBtn = document.getElementById('concierge-send');
  var log = document.getElementById('concierge-log');
  if (!dock || !toggleBtn || !panel || !form || !input || !log) return;

  var history = [];
  var busy = false;

  function csrfToken() {
    var field = form.querySelector('[name=csrfmiddlewaretoken]');
    return field ? field.value : '';
  }

  function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /* The model writes markdown, so render the little of it that a chat bubble
   * needs. Everything is escaped first: these are tags we add, never tags the
   * model sent. */
  function inline(text) {
    return escapeHtml(text)
      .replace(/\[([^\]]{1,80})\]\((\/[a-z0-9_\-\/]{2,120})\)/gi,
               '<a href="$2">$1</a>')
      .replace(/(^|[\s(])(\/[a-z0-9_\-]+(?:\/[a-z0-9_\-]+)+)/gi,
               '$1<a href="$2">$2</a>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[\s(])_([^_]+)_(?=[\s.,;:!?)]|$)/g, '$1<em>$2</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>');
  }

  function renderMarkdown(text) {
    var html = '';
    String(text).split(/\n{2,}/).forEach(function (block) {
      var lines = block.split('\n');
      var bulleted = lines.every(function (l) { return /^\s*[-*]\s+/.test(l); });
      var numbered = lines.every(function (l) { return /^\s*\d+[.)]\s+/.test(l); });
      if (bulleted || numbered) {
        var tag = numbered ? 'ol' : 'ul';
        html += '<' + tag + '>';
        lines.forEach(function (l) {
          html += '<li>' + inline(l.replace(/^\s*(?:[-*]|\d+[.)])\s+/, '')) + '</li>';
        });
        html += '</' + tag + '>';
        return;
      }
      var heading = block.match(/^#{1,4}\s+(.*)$/);
      if (heading) {
        html += '<p><strong>' + inline(heading[1]) + '</strong></p>';
        return;
      }
      html += '<p>' + lines.map(inline).join('<br>') + '</p>';
    });
    return html;
  }

  function addMessage(role, text) {
    var wrap = document.createElement('div');
    wrap.className = 'concierge-msg concierge-msg-' + role;
    wrap.innerHTML = renderMarkdown(text);
    log.appendChild(wrap);
    log.scrollTop = log.scrollHeight;
    return wrap;
  }

  function addBrief(brief) {
    var rows = [
      ['Where', brief.destination],
      ['When', brief.dates],
      ['Who', brief.group],
      ['Budget', brief.budget],
      ['Looking for', brief.interests],
      ['Notes', brief.notes]
    ].filter(function (row) { return row[1]; });

    var html = '<h3>Your brief so far</h3><dl>';
    rows.forEach(function (row) {
      html += '<dt>' + escapeHtml(row[0]) + '</dt><dd>' + escapeHtml(row[1]) + '</dd>';
    });
    html += '</dl>';

    if (brief.candidates && brief.candidates.length) {
      html += '<ul>';
      brief.candidates.forEach(function (c) {
        html += '<li><a href="/' + escapeHtml(c.path) + '">' + escapeHtml(c.title) + '</a>';
        if (c.why) html += ' — ' + escapeHtml(c.why);
        html += '</li>';
      });
      html += '</ul>';
    }

    var card = document.createElement('div');
    card.className = 'concierge-brief';
    card.innerHTML = html;
    log.appendChild(card);
    log.scrollTop = log.scrollHeight;
  }

  function setBusy(state) {
    busy = state;
    sendBtn.disabled = state;
    sendBtn.textContent = state ? '…' : 'Send';
  }

  function send(text) {
    history.push({ role: 'user', content: text });
    addMessage('you', text);
    input.value = '';
    setBusy(true);

    var thinking = addMessage('bot', 'Looking through the guide…');
    thinking.classList.add('concierge-typing');

    fetch('/concierge/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
      body: JSON.stringify({ messages: history, path: window.W66_CONCIERGE_PATH || '' })
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        thinking.remove();
        if (!res.ok || res.data.error) {
          addMessage('error', res.data.error || 'Something went wrong. Please try again.');
          return;
        }
        if (res.data.reply) {
          history.push({ role: 'assistant', content: res.data.reply });
          addMessage('bot', res.data.reply);
        }
        if (res.data.brief) addBrief(res.data.brief);
      })
      .catch(function () {
        thinking.remove();
        addMessage('error', 'Could not reach the concierge. Please try again.');
      })
      .then(function () { setBusy(false); input.focus(); });
  }

  /* The top bar is sticky and stays usable, so the drawer starts under it. */
  function syncTop() {
    var nav = document.querySelector('.topnav');
    if (nav) dock.style.setProperty('--concierge-top', nav.offsetHeight + 'px');
  }

  syncTop();
  window.addEventListener('resize', syncTop);

  function isOpen() {
    return dock.getAttribute('data-open') === 'true';
  }

  function setOpen(open) {
    dock.setAttribute('data-open', open ? 'true' : 'false');
    toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (toggleLabel) toggleLabel.textContent = open ? 'Close' : OPEN_LABEL;
    if (toggleIcon) toggleIcon.textContent = open ? '\u00d7' : '\u2726';
    toggleBtn.setAttribute('aria-label', open ? 'Close the concierge' : OPEN_LABEL);
    panel.inert = !open;
    if (open) input.focus();
  }

  setOpen(false);

  toggleBtn.addEventListener('click', function () { setOpen(!isOpen()); });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && isOpen()) setOpen(false);
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var text = input.value.trim();
    if (text && !busy) send(text);
  });

  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      form.dispatchEvent(new Event('submit', { cancelable: true }));
    }
  });
})();
