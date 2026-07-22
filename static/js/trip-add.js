/* Add to Trip — modal that adds a POI or place to a tab.bi trip */
(function () {
  var modal = document.getElementById('trip-modal');
  if (!modal) return;

  var csrfInput = modal.querySelector('input[name=csrfmiddlewaretoken]');
  var errorBox = document.getElementById('trip-modal-error');
  var stepPassphrase = document.getElementById('trip-modal-step-passphrase');
  var stepConfirm = document.getElementById('trip-modal-step-confirm');
  var stepSuccess = document.getElementById('trip-modal-step-success');
  var passphraseInput = document.getElementById('trip-modal-passphrase');
  var findBtn = document.getElementById('trip-modal-find');
  var confirmBtn = document.getElementById('trip-modal-confirm');
  var notThisTripBtn = document.getElementById('trip-modal-not-this-trip');
  var placeTitleEl = document.getElementById('trip-modal-place-title');
  var planTitleEl = document.getElementById('trip-modal-plan-title');
  var successMessageEl = document.getElementById('trip-modal-success-message');
  var viewLink = document.getElementById('trip-modal-view-link');

  var STORAGE_KEY = 'world66_tabbi_trip';

  var current = null;       // {path, cityPath, title} of the clicked button
  var selectedPlan = null;  // {slug, title, passphrase}

  function showStep(step) {
    stepPassphrase.style.display = step === 'passphrase' ? '' : 'none';
    stepConfirm.style.display = step === 'confirm' ? '' : 'none';
    stepSuccess.style.display = step === 'success' ? '' : 'none';
  }

  function showError(message) {
    errorBox.textContent = message || '';
    errorBox.style.display = message ? '' : 'none';
  }

  function postJSON(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfInput.value },
      body: JSON.stringify(body),
    }).then(function (r) { return r.json(); });
  }

  function rememberPlan() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        passphrase: selectedPlan.passphrase,
        slug: selectedPlan.slug,
        title: selectedPlan.title,
      }));
    } catch (err) { /* localStorage unavailable — remembering is a convenience, not required */ }
  }

  function findTrip(passphrase, silent) {
    showError('');
    return postJSON('/tabbi/plans', { passphrase: passphrase }).then(function (data) {
      if (data.error || !data.plans || !data.plans.length) {
        if (!silent) showError(data.error || 'No trip found for that passphrase.');
        showStep('passphrase');
        return;
      }
      var plan = data.plans[0];
      selectedPlan = { slug: plan.slug, title: plan.title, passphrase: passphrase };
      placeTitleEl.textContent = current.title;
      planTitleEl.textContent = plan.title;
      showStep('confirm');
    }, function () {
      if (!silent) showError('Could not reach tab.bi. Please try again later.');
      showStep('passphrase');
    });
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest ? e.target.closest('.trip-add-btn') : null;
    if (!btn) return;
    current = {
      path: btn.getAttribute('data-path'),
      cityPath: btn.getAttribute('data-city-path'),
      title: btn.getAttribute('data-title'),
    };
    selectedPlan = null;
    showError('');

    var remembered = null;
    try { remembered = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null'); } catch (err) { /* ignore */ }

    if (remembered && remembered.passphrase) {
      passphraseInput.value = remembered.passphrase;
      showStep('passphrase');
      modal.showModal();
      findTrip(remembered.passphrase, true);
    } else {
      passphraseInput.value = '';
      showStep('passphrase');
      modal.showModal();
    }
  });

  findBtn.addEventListener('click', function () {
    var passphrase = passphraseInput.value.trim();
    if (!passphrase) { showError('Enter a passphrase.'); return; }
    findTrip(passphrase, false);
  });

  notThisTripBtn.addEventListener('click', function () {
    selectedPlan = null;
    passphraseInput.value = '';
    showError('');
    showStep('passphrase');
  });

  confirmBtn.addEventListener('click', function () {
    if (!selectedPlan || !current) return;
    showError('');
    postJSON('/tabbi/add-to-trip', {
      passphrase: selectedPlan.passphrase,
      plan_slug: selectedPlan.slug,
      city_path: current.cityPath,
      poi_path: current.path,
    }).then(function (data) {
      if (data.error) {
        showError(data.error);
        return;
      }
      rememberPlan();
      successMessageEl.textContent = 'Added ' + current.title + ' to ' + selectedPlan.title + '.';
      if (data.trip_url) {
        viewLink.href = data.trip_url;
        viewLink.style.display = '';
      } else {
        viewLink.style.display = 'none';
      }
      showStep('success');
    }, function () {
      showError('Could not reach tab.bi. Please try again later.');
    });
  });
})();
