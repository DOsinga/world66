/* Travel profile widget — collapsible dimension rows with row highlight */
(function () {
  var card = document.getElementById('score-profile-card');
  if (!card) return;

  var toggle = document.getElementById('score-profile-toggle');
  var body = document.getElementById('score-profile-body');
  var toggleLabel = toggle.querySelector('.score-profile-toggle-label');
  var toggleGlyph = toggle.querySelector('.score-profile-toggle-glyph');
  var rows = card.querySelectorAll('.score-profile-row');

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
      row.addEventListener('mouseenter', function () { highlight(row, true); });
      row.addEventListener('mouseleave', function () { highlight(row, false); });
      row.addEventListener('focus', function () { highlight(row, true); });
      row.addEventListener('blur', function () { highlight(row, false); });
    })(rows[i]);
  }
})();
