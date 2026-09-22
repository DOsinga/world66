/* Concierge overlay.
 *
 * The transcript lives here in the browser and is posted back whole with each
 * turn: there is no database on this site, and the server keeps no session.
 */
(function () {
  var openBtn = document.getElementById('concierge-open');
  var panel = document.getElementById('concierge-panel');
  var closeBtn = document.getElementById('concierge-close');
  var form = document.getElementById('concierge-form');
  var input = document.getElementById('concierge-input');
  var sendBtn = document.getElementById('concierge-send');
  var log = document.getElementById('concierge-log');
  if (!openBtn || !panel || !form || !input || !log) return;

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

  /* Turn markdown links and bare guide paths into real links; everything else
   * stays inert text, because it came from a model. */
  function linkify(escaped) {
    return escaped
      .replace(/\[([^\]]{1,80})\]\((\/[a-z0-9_\-\/]{2,120})\)/gi,
               '<a href="$2">$1</a>')
      .replace(/(^|[\s(])(\/[a-z0-9_\-]+(?:\/[a-z0-9_\-]+)+)/gi,
               '$1<a href="$2">$2</a>');
  }

  function addMessage(role, text) {
    var wrap = document.createElement('div');
    wrap.className = 'concierge-msg concierge-msg-' + role;
    var paragraphs = String(text).split(/\n{2,}/);
    wrap.innerHTML = paragraphs
      .map(function (p) { return '<p>' + linkify(escapeHtml(p)).replace(/\n/g, '<br>') + '</p>'; })
      .join('');
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

  function openPanel() {
    panel.hidden = false;
    openBtn.style.display = 'none';
    openBtn.setAttribute('aria-expanded', 'true');
    input.focus();
  }

  function closePanel() {
    panel.hidden = true;
    openBtn.style.display = '';
    openBtn.setAttribute('aria-expanded', 'false');
  }

  openBtn.addEventListener('click', openPanel);
  if (closeBtn) closeBtn.addEventListener('click', closePanel);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !panel.hidden) closePanel();
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
