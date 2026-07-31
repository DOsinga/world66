/* Travel profile widget — collapsible dimension rows with hover/focus reasoning */
(function () {
  var card = document.getElementById('score-profile-card');
  if (!card) return;

  var toggle = document.getElementById('score-profile-toggle');
  var body = document.getElementById('score-profile-body');
  var note = document.getElementById('score-profile-note');
  var toggleLabel = toggle.querySelector('.score-profile-toggle-label');
  var toggleGlyph = toggle.querySelector('.score-profile-toggle-glyph');
  var rows = card.querySelectorAll('.score-profile-row');
  var idleNote = note.textContent;

  function setExpanded(expanded) {
    toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    toggleLabel.textContent = expanded
      ? toggleLabel.getAttribute('data-expanded-label')
      : toggleLabel.getAttribute('data-collapsed-label');
    toggleGlyph.textContent = expanded ? '−' : '+';
    body.style.maxHeight = expanded ? body.scrollHeight + 'px' : '0px';
  }

  setExpanded(false);

  toggle.addEventListener('click', function () {
    setExpanded(toggle.getAttribute('aria-expanded') !== 'true');
  });

  function highlight(row, on) {
    row.classList.toggle('is-active', on);
  }

  for (var i = 0; i < rows.length; i++) {
    (function (row) {
      var blurb = row.getAttribute('data-blurb');
      function show() { highlight(row, true); note.textContent = blurb; }
      function hide() { highlight(row, false); note.textContent = idleNote; }
      row.addEventListener('mouseenter', show);
      row.addEventListener('mouseleave', hide);
      row.addEventListener('focus', show);
      row.addEventListener('blur', hide);
    })(rows[i]);
  }
})();
