const bookingConfig = window.FISIOLOGICO_BOOKING ?? {};
const bookingRoot = document.querySelector('[data-booking-app]');

if (bookingRoot) {
  const status = bookingRoot.querySelector('[data-booking-status]');
  const dates = bookingRoot.querySelector('[data-booking-dates]');
  const times = bookingRoot.querySelector('[data-booking-times]');
  const form = bookingRoot.querySelector('[data-booking-form]');
  const summary = bookingRoot.querySelector('[data-booking-summary]');
  const submit = bookingRoot.querySelector('[data-booking-submit]');
  const success = bookingRoot.querySelector('[data-booking-success]');
  const challenge = bookingRoot.querySelector('[data-turnstile]');
  let availableSlots = [];
  let selectedSlot = '';
  let turnstileToken = '';
  let durationMinutes = 50;

  const configured = Boolean(bookingConfig.endpoint && bookingConfig.publishableKey && bookingConfig.turnstileSiteKey);
  const apiHeaders = {
    apikey: bookingConfig.publishableKey || '',
    'Content-Type': 'application/json',
  };

  const setStatus = (message, state = '') => {
    status.textContent = message;
    status.dataset.state = state;
  };

  const longDate = (iso) => new Intl.DateTimeFormat('es-ES', {
    weekday: 'long', day: 'numeric', month: 'long', timeZone: 'Europe/Madrid',
  }).format(new Date(iso));

  const shortDate = (iso) => new Intl.DateTimeFormat('es-ES', {
    weekday: 'short', day: 'numeric', month: 'short', timeZone: 'Europe/Madrid',
  }).format(new Date(iso));

  const timeLabel = (iso) => new Intl.DateTimeFormat('es-ES', {
    hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Madrid',
  }).format(new Date(iso));

  const dayKey = (iso) => new Intl.DateTimeFormat('sv-SE', {
    year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'Europe/Madrid',
  }).format(new Date(iso));

  const paymentState = new URLSearchParams(location.search).get('payment');
  if (paymentState === 'success') {
    form.hidden = true;
    dates.hidden = true;
    times.hidden = true;
    status.hidden = true;
    success.hidden = false;
    const storedSlot = sessionStorage.getItem('fisiologicoBookingSlot');
    success.querySelector('[data-success-date]').textContent = storedSlot ? `${longDate(storedSlot)}, ${timeLabel(storedSlot)}` : '';
    success.focus();
  } else if (paymentState === 'cancelled') {
    setStatus('El pago no se ha completado y la cita no está confirmada. El hueco se liberará automáticamente.', 'error');
  }

  const renderTimes = (key) => {
    selectedSlot = '';
    form.hidden = true;
    summary.textContent = '';
    const slots = availableSlots.filter((slot) => dayKey(slot) === key);
    times.replaceChildren(...slots.map((slot) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'booking-time';
      button.textContent = timeLabel(slot);
      button.addEventListener('click', () => {
        times.querySelectorAll('button').forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
        selectedSlot = slot;
        summary.textContent = `${longDate(slot)}, ${timeLabel(slot)} · videollamada de ${durationMinutes} minutos`;
        form.hidden = false;
        form.querySelector('input:not([type="hidden"])')?.focus();
      });
      button.setAttribute('aria-pressed', 'false');
      return button;
    }));
  };

  const renderAvailability = () => {
    const uniqueDays = [...new Set(availableSlots.map(dayKey))];
    if (!uniqueDays.length) {
      setStatus('No hay huecos online disponibles en las próximas semanas. Puedes consultarnos por WhatsApp.', 'empty');
      return;
    }
    setStatus('Elige primero un día y después una hora.', 'ready');
    dates.replaceChildren(...uniqueDays.map((key, index) => {
      const firstSlot = availableSlots.find((slot) => dayKey(slot) === key);
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'booking-day';
      button.textContent = shortDate(firstSlot);
      button.setAttribute('aria-pressed', String(index === 0));
      button.addEventListener('click', () => {
        dates.querySelectorAll('button').forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
        renderTimes(key);
      });
      return button;
    }));
    renderTimes(uniqueDays[0]);
  };

  const loadAvailability = async () => {
    if (!configured) {
      setStatus('La agenda online está preparada, pero todavía no está activada. Mientras tanto puedes reservar por WhatsApp.', 'offline');
      return;
    }
    setStatus('Consultando la agenda…', 'loading');
    try {
      const from = new Date().toISOString().slice(0, 10);
      const response = await fetch(`${bookingConfig.endpoint}?from=${from}&days=21`, { headers: apiHeaders });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      availableSlots = result.slots ?? [];
      durationMinutes = result.durationMinutes ?? durationMinutes;
      document.querySelector('[data-booking-duration]').textContent = `${durationMinutes} minutos`;
      renderAvailability();
    } catch {
      setStatus('No hemos podido consultar la agenda. Puedes intentarlo más tarde o pedir cita por WhatsApp.', 'error');
    }
  };

  const loadTurnstile = () => {
    if (!configured || !challenge) return;
    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
    script.async = true;
    script.defer = true;
    script.addEventListener('load', () => {
      window.turnstile.render(challenge, {
        sitekey: bookingConfig.turnstileSiteKey,
        action: 'online-booking',
        callback: (token) => { turnstileToken = token; },
        'expired-callback': () => { turnstileToken = ''; },
        'error-callback': () => { turnstileToken = ''; },
        theme: 'light',
      });
    });
    document.head.appendChild(script);
  };

  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!selectedSlot || !turnstileToken) {
      setStatus('Selecciona una hora y completa la comprobación de seguridad.', 'error');
      return;
    }
    submit.disabled = true;
    submit.textContent = 'Confirmando…';
    const fields = new FormData(form);
    try {
      const response = await fetch(bookingConfig.endpoint, {
        method: 'POST',
        headers: apiHeaders,
        body: JSON.stringify({
          startsAt: selectedSlot,
          name: fields.get('name'),
          email: fields.get('email'),
          phone: fields.get('phone'),
          website: fields.get('website'),
          privacyAccepted: fields.get('privacy') === 'on',
          turnstileToken,
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'No se pudo confirmar la cita.');
      sessionStorage.setItem('fisiologicoBookingSlot', result.startsAt);
      window.location.assign(result.checkoutUrl);
    } catch (error) {
      setStatus(error.message || 'No se pudo confirmar la cita.', 'error');
      turnstileToken = '';
      window.turnstile?.reset();
    } finally {
      submit.disabled = false;
      submit.textContent = 'Continuar al pago · 70 €';
    }
  });

  if (paymentState !== 'success') {
    loadTurnstile();
    loadAvailability();
  }
}
