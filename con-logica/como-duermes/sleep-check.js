(() => {
  const form = document.querySelector('[data-sleep-form]');
  if (!form) return;
  const author = document.querySelector('.thought-author');
  if (author) author.before(document.querySelector('.sleep-check'));
  const steps = Array.from(form.querySelectorAll('[data-step]'));
  const next = form.querySelector('[data-sleep-next]');
  const back = form.querySelector('[data-sleep-back]');
  const submit = form.querySelector('[data-sleep-submit]');
  const error = form.querySelector('[data-sleep-error]');
  const stepLabel = form.querySelector('[data-step-label]');
  const progress = form.querySelector('[data-sleep-progress]');
  const result = document.querySelector('[data-sleep-result]');
  let current = 0;
  const value = (name) => Number(form.elements[name].value);
  const level = (score) => score < 1 ? 'estable' : score < 2 ? 'conviene observar' : 'merece atención';
  function update() {
    steps.forEach((step, index) => { step.hidden = index !== current; });
    back.hidden = current === 0;
    next.hidden = current === steps.length - 1;
    submit.hidden = current !== steps.length - 1;
    stepLabel.textContent = 'Paso ' + (current + 1) + ' de ' + steps.length;
    progress.style.width = (((current + 1) / steps.length) * 100) + '%';
    error.hidden = true;
  }
  function validStep() {
    const fields = Array.from(steps[current].querySelectorAll('select'));
    const valid = fields.every((field) => field.value !== '');
    if (!valid) {
      error.hidden = false;
      const missing = fields.find((field) => field.value === '');
      if (missing) missing.focus();
    }
    return valid;
  }
  next.addEventListener('click', () => { if (validStep()) { current += 1; update(); } });
  back.addEventListener('click', () => { current -= 1; update(); });
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (!validStep()) return;
    const domains = [
      { name: 'Inicio', score: (value('latency') + value('onsetFrequency')) / 2, text: 'Tiempo y frecuencia con que te cuesta dormirte.' },
      { name: 'Continuidad', score: (value('maintenance') + value('wakeTime')) / 2, text: 'Despertares y tiempo que permaneces despierto.' },
      { name: 'Recuperación', score: (value('restoration') + value('fatigue')) / 2, text: 'Cómo despiertas y cuánto condiciona el cansancio.' },
      { name: 'Ritmo', score: (value('duration') + value('regularity')) / 2, text: 'Duración aproximada y estabilidad de horarios.' },
      { name: 'Impacto diurno', score: (value('safetySleepiness') + value('sleepAids')) / 2, text: 'Somnolencia con atención y apoyos para dormir.' }
    ];
    const priority = domains.slice().sort((a, b) => b.score - a.score)[0];
    const alerts = [];
    if (value('safetySleepiness') === 3) alerts.push('<strong>Somnolencia al volante:</strong> evita conducir cuando notes sueño y solicita valoración sanitaria.');
    if (value('breathing') === 3) alerts.push('<strong>Pausas, ahogos o ronquidos intensos:</strong> coméntalo con tu médico; esta herramienta no descarta apnea.');
    const segments = domains.map((item) => {
      const tone = item.score < 1 ? 'low' : item.score < 2 ? 'mid' : 'high';
      return '<li class="sleep-domain sleep-domain--' + tone + '"><span>' + item.name + '</span><strong>' + level(item.score) + '</strong><small>' + item.text + '</small></li>';
    }).join('');
    const alertHtml = alerts.length ? '<div class="sleep-alert">' + alerts.map((item) => '<p>' + item + '</p>').join('') + '</div>' : '';
    result.innerHTML = '<p class="sleep-result-kicker">Tu noche, por dimensiones</p><h2>' +
      (alerts.length ? 'Hay algo que conviene priorizar.' : 'Empieza observando: ' + priority.name.toLowerCase() + '.') +
      '</h2><p>' + (alerts.length ? 'Estas señales son más importantes que el resto del perfil.' : 'No es una nota ni un diagnóstico. Es un mapa para conversar con más precisión.') +
      '</p>' + alertHtml + '<ol class="sleep-domains">' + segments +
      '</ol><div class="sleep-result-guidance"><h3>Qué puedes llevar a una consulta</h3><p>Durante una o dos semanas anota la hora de acostarte, el tiempo hasta dormirte, los despertares, qué parecía provocarlos y cómo funcionaste al día siguiente.</p></div><button class="sleep-button sleep-button-secondary" type="button" data-sleep-restart>Repetir la exploración</button>';
    form.hidden = true;
    result.hidden = false;
    result.focus();
    result.querySelector('[data-sleep-restart]').addEventListener('click', () => {
      form.reset(); current = 0; update(); result.hidden = true; form.hidden = false;
      form.querySelector('select').focus();
    });
  });
  update();
})();
