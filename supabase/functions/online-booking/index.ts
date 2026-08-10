import { createClient, type SupabaseClient } from 'npm:@supabase/supabase-js@2.95.0'
import { addUtcDays, type BusyPeriod, overlaps, parseDate, zonedDateTimeToUtc } from '../_shared/time.ts'

type BookingSettings = {
  active: boolean
  timezone: string
  duration_minutes: number
  slot_interval_minutes: number
  min_notice_hours: number
  max_days_ahead: number
}

type AvailabilityRule = {
  weekday: number
  starts_at: string
  ends_at: string
}

const PROD_ORIGINS = ['https://www.elfisiologico.com', 'https://elfisiologico.com']
const LOCAL_ORIGIN = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/
const BOOKING_PRICE_CENTS = 7000
const CHECKOUT_MINUTES = 30
const HOLD_MINUTES = 35

const json = (body: unknown, status: number, headers: HeadersInit) =>
  Response.json(body, { status, headers })

function allowedOrigins(): string[] {
  const configured = Deno.env.get('BOOKING_ALLOWED_ORIGINS')
  return configured
    ? configured.split(',').map((origin) => origin.trim()).filter(Boolean)
    : PROD_ORIGINS
}

function corsHeaders(req: Request): Record<string, string> | null {
  const origin = req.headers.get('origin') ?? ''
  const allowed = allowedOrigins().includes(origin) || LOCAL_ORIGIN.test(origin)
  if (origin && !allowed) return null
  return {
    'Access-Control-Allow-Origin': origin || PROD_ORIGINS[0],
    'Access-Control-Allow-Headers': 'apikey, content-type, x-client-info',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Content-Type': 'application/json; charset=utf-8',
    'Vary': 'Origin',
    'Cache-Control': 'no-store',
  }
}

function requiredEnv(name: string): string {
  const value = Deno.env.get(name)
  if (!value) throw new Error(`Missing environment variable: ${name}`)
  return value
}

function secretKey(): string {
  const legacy = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
  if (legacy) return legacy
  const keys = JSON.parse(requiredEnv('SUPABASE_SECRET_KEYS')) as Record<string, string>
  const value = keys.default ?? Object.values(keys)[0]
  if (!value) throw new Error('No Supabase secret key is configured')
  return value
}

function adminClient(): SupabaseClient {
  return createClient(requiredEnv('SUPABASE_URL'), secretKey(), {
    auth: { persistSession: false, autoRefreshToken: false },
  })
}

async function googleAccessToken(): Promise<string> {
  const response = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: requiredEnv('GOOGLE_CLIENT_ID'),
      client_secret: requiredEnv('GOOGLE_CLIENT_SECRET'),
      refresh_token: requiredEnv('GOOGLE_REFRESH_TOKEN'),
      grant_type: 'refresh_token',
    }),
  })
  const data = await response.json()
  if (!response.ok || !data.access_token) throw new Error('Google OAuth token refresh failed')
  return data.access_token as string
}

async function stripeRequest(path: string, body: URLSearchParams): Promise<Record<string, any>> {
  const response = await fetch(`https://api.stripe.com/v1/${path}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${requiredEnv('STRIPE_SECRET_KEY')}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body,
  })
  const data = await response.json()
  if (!response.ok) throw new Error(`Stripe request failed (${response.status}): ${data.error?.code ?? 'unknown'}`)
  return data
}

async function createCheckoutSession(appointmentId: string, email: string, startsAt: Date): Promise<Record<string, any>> {
  const siteUrl = allowedOrigins()[0] ?? PROD_ORIGINS[0]
  const startLabel = new Intl.DateTimeFormat('es-ES', {
    dateStyle: 'full', timeStyle: 'short', timeZone: 'Europe/Madrid',
  }).format(startsAt)
  const body = new URLSearchParams({
    mode: 'payment',
    locale: 'es',
    customer_email: email,
    client_reference_id: appointmentId,
      success_url: `${siteUrl}/cita-online/?payment=success`,
    cancel_url: `${siteUrl}/cita-online/?payment=cancelled`,
    expires_at: String(Math.floor(Date.now() / 1000) + CHECKOUT_MINUTES * 60),
    'payment_method_types[0]': 'card',
    'metadata[appointment_id]': appointmentId,
    'payment_intent_data[metadata][appointment_id]': appointmentId,
    'payment_intent_data[receipt_email]': email,
    'line_items[0][price_data][currency]': 'eur',
    'line_items[0][price_data][unit_amount]': String(BOOKING_PRICE_CENTS),
    'line_items[0][price_data][product_data][name]': 'Consulta online · FisioLógico',
    'line_items[0][price_data][product_data][description]': `${startLabel} · 50 minutos · Google Meet`,
    'line_items[0][quantity]': '1',
  })
  return await stripeRequest('checkout/sessions', body)
}

function timingSafeEqual(left: Uint8Array, right: Uint8Array): boolean {
  if (left.length !== right.length) return false
  let mismatch = 0
  for (let index = 0; index < left.length; index += 1) mismatch |= left[index] ^ right[index]
  return mismatch === 0
}

function hexToBytes(value: string): Uint8Array | null {
  if (!/^[a-f0-9]{64}$/i.test(value)) return null
  return new Uint8Array(value.match(/.{2}/g)!.map((byte) => Number.parseInt(byte, 16)))
}

async function verifyStripeSignature(payload: string, signatureHeader: string): Promise<boolean> {
  const parts = signatureHeader.split(',').map((part) => part.split('=', 2))
  const timestamp = parts.find(([key]) => key === 't')?.[1]
  const signatures = parts.filter(([key]) => key === 'v1').map(([, value]) => value)
  if (!timestamp || signatures.length === 0 || Math.abs(Date.now() / 1000 - Number(timestamp)) > 300) return false
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(requiredEnv('STRIPE_WEBHOOK_SECRET')),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  )
  const expected = new Uint8Array(await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(`${timestamp}.${payload}`)))
  return signatures.some((signature) => {
    const actual = hexToBytes(signature)
    return actual ? timingSafeEqual(expected, actual) : false
  })
}

async function googleBusy(token: string, timeMin: string, timeMax: string): Promise<BusyPeriod[]> {
  const calendarId = requiredEnv('GOOGLE_CALENDAR_ID')
  const response = await fetch('https://www.googleapis.com/calendar/v3/freeBusy', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ timeMin, timeMax, items: [{ id: calendarId }] }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error('Google Calendar availability check failed')
  return data.calendars?.[calendarId]?.busy ?? []
}

async function loadConfiguration(supabase: SupabaseClient): Promise<{ settings: BookingSettings; rules: AvailabilityRule[] }> {
  const [{ data: settings, error: settingsError }, { data: rules, error: rulesError }] = await Promise.all([
    supabase.from('booking_settings').select('*').eq('id', true).single(),
    supabase.from('booking_availability').select('weekday, starts_at, ends_at').eq('active', true).order('weekday').order('starts_at'),
  ])
  if (settingsError || rulesError || !settings) throw new Error('Booking configuration is incomplete')
  return { settings: settings as BookingSettings, rules: (rules ?? []) as AvailabilityRule[] }
}

async function availableSlots(
  supabase: SupabaseClient,
  startDate: Date,
  days: number,
  accessToken: string,
): Promise<{ timezone: string; durationMinutes: number; slots: string[] }> {
  const { settings, rules } = await loadConfiguration(supabase)
  if (!settings.active || rules.length === 0) {
    return { timezone: settings.timezone, durationMinutes: settings.duration_minutes, slots: [] }
  }

  const now = new Date()
  const earliest = new Date(now.getTime() + settings.min_notice_hours * 3_600_000)
  const latestAllowed = new Date(now.getTime() + settings.max_days_ahead * 86_400_000)
  const rangeEndDate = addUtcDays(startDate, days)
  const rangeStart = zonedDateTimeToUtc(startDate.toISOString().slice(0, 10), '00:00', settings.timezone)
  const rangeEnd = zonedDateTimeToUtc(rangeEndDate.toISOString().slice(0, 10), '00:00', settings.timezone)

  await supabase
    .from('online_appointments')
    .update({ status: 'expired', updated_at: now.toISOString() })
    .eq('status', 'awaiting_payment')
    .lt('hold_expires_at', now.toISOString())

  const [{ data: booked, error }, calendarBusy] = await Promise.all([
    supabase
      .from('online_appointments')
      .select('starts_at, ends_at')
      .in('status', ['awaiting_payment', 'payment_received', 'confirmed'])
      .lt('starts_at', rangeEnd.toISOString())
      .gt('ends_at', rangeStart.toISOString()),
    googleBusy(accessToken, rangeStart.toISOString(), rangeEnd.toISOString()),
  ])
  if (error) throw new Error('Could not read existing appointments')
  const bookedBusy: BusyPeriod[] = (booked ?? []).map((appointment) => ({
    start: appointment.starts_at,
    end: appointment.ends_at,
  }))
  const busy = [...calendarBusy, ...bookedBusy]
  const slots: string[] = []

  for (let index = 0; index < days; index += 1) {
    const date = addUtcDays(startDate, index)
    const dateText = date.toISOString().slice(0, 10)
    const weekday = date.getUTCDay() || 7
    for (const rule of rules.filter((item) => item.weekday === weekday)) {
      let slotStart = zonedDateTimeToUtc(dateText, rule.starts_at, settings.timezone)
      const ruleEnd = zonedDateTimeToUtc(dateText, rule.ends_at, settings.timezone)
      while (slotStart < ruleEnd) {
        const slotEnd = new Date(slotStart.getTime() + settings.duration_minutes * 60_000)
        if (slotEnd <= ruleEnd && slotStart >= earliest && slotStart <= latestAllowed && !busy.some((item) => overlaps(slotStart, slotEnd, item))) {
          slots.push(slotStart.toISOString())
        }
        slotStart = new Date(slotStart.getTime() + settings.slot_interval_minutes * 60_000)
      }
    }
  }
  return { timezone: settings.timezone, durationMinutes: settings.duration_minutes, slots }
}

async function verifyTurnstile(token: string, remoteIp: string | null): Promise<boolean> {
  const secret = requiredEnv('TURNSTILE_SECRET_KEY')
  if (!token) return false
  const response = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ secret, response: token, ...(remoteIp ? { remoteip: remoteIp } : {}) }),
  })
  const result = await response.json()
  const allowedHostnames = allowedOrigins().map((origin) => new URL(origin).hostname)
  return response.ok &&
    result.success === true &&
    result.action === 'online-booking' &&
    allowedHostnames.includes(result.hostname)
}

function cleanText(value: unknown, max: number): string {
  return typeof value === 'string' ? value.trim().replace(/\s+/g, ' ').slice(0, max) : ''
}

function validEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) && value.length <= 254
}

async function createGoogleEvent(
  token: string,
  appointmentId: string,
  name: string,
  email: string,
  start: Date,
  end: Date,
  timezone: string,
) {
  const calendarId = requiredEnv('GOOGLE_CALENDAR_ID')
  const eventId = `fisio${appointmentId.replaceAll('-', '')}`
  const params = new URLSearchParams({ conferenceDataVersion: '1', sendUpdates: 'all' })
  const response = await fetch(`https://www.googleapis.com/calendar/v3/calendars/${encodeURIComponent(calendarId)}/events?${params}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      id: eventId,
      summary: 'Consulta online · FisioLógico',
      description: 'Consulta online con Fran. La información clínica se tratará durante la consulta, no por correo.',
      start: { dateTime: start.toISOString(), timeZone: timezone },
      end: { dateTime: end.toISOString(), timeZone: timezone },
      attendees: [{ email, displayName: name }],
      conferenceData: { createRequest: { requestId: appointmentId, conferenceSolutionKey: { type: 'hangoutsMeet' } } },
      reminders: { useDefault: false, overrides: [{ method: 'email', minutes: 1440 }, { method: 'popup', minutes: 15 }] },
      extendedProperties: { private: { fisiologicoAppointmentId: appointmentId } },
    }),
  })
  const event = await response.json()
  if (response.status === 409) {
    const existing = await fetch(`https://www.googleapis.com/calendar/v3/calendars/${encodeURIComponent(calendarId)}/events/${eventId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (existing.ok) return await existing.json()
  }
  if (!response.ok) throw new Error(`Google event creation failed (${response.status})`)
  return event
}

async function handleStripeWebhook(req: Request, supabase: SupabaseClient): Promise<Response> {
  const rawBody = await req.text()
  const signature = req.headers.get('stripe-signature') ?? ''
  if (!await verifyStripeSignature(rawBody, signature)) return new Response('Invalid signature', { status: 400 })
  const event = JSON.parse(rawBody)
  if (event.type !== 'checkout.session.completed') return Response.json({ received: true })

  const session = event.data?.object
  const appointmentId = session?.metadata?.appointment_id
  if (!appointmentId || session.payment_status !== 'paid' || session.amount_total !== BOOKING_PRICE_CENTS || session.currency !== 'eur') {
    return new Response('Invalid checkout data', { status: 400 })
  }

  const { data: existing, error: readError } = await supabase
    .from('online_appointments')
    .select('id, patient_name, patient_email, starts_at, ends_at, timezone, status')
    .eq('id', appointmentId)
    .maybeSingle()
  if (readError || !existing) throw new Error('Paid appointment does not exist')
  if (existing.status === 'confirmed') return Response.json({ received: true })
  if (!['awaiting_payment', 'payment_received'].includes(existing.status)) throw new Error('Paid appointment is not available for confirmation')

  if (existing.status === 'awaiting_payment') {
    const { error: paymentError } = await supabase.from('online_appointments').update({
      status: 'payment_received',
      stripe_checkout_session_id: session.id,
      stripe_payment_intent_id: session.payment_intent,
      updated_at: new Date().toISOString(),
    }).eq('id', appointmentId).eq('status', 'awaiting_payment')
    if (paymentError) throw new Error(`Payment persistence failed: ${paymentError.code}`)
  }
  const appointment = existing

  const googleToken = await googleAccessToken()
  const googleEvent = await createGoogleEvent(
    googleToken,
    appointment.id,
    appointment.patient_name,
    appointment.patient_email,
    new Date(appointment.starts_at),
    new Date(appointment.ends_at),
    appointment.timezone,
  )
  const { error: confirmError } = await supabase.from('online_appointments').update({
    status: 'confirmed',
    google_event_id: googleEvent.id,
    google_event_url: googleEvent.htmlLink ?? null,
    meet_url: googleEvent.hangoutLink ?? null,
    updated_at: new Date().toISOString(),
  }).eq('id', appointment.id).eq('status', 'payment_received')
  if (confirmError) throw new Error('Paid appointment confirmation failed')
  return Response.json({ received: true })
}

async function handleAvailability(req: Request, supabase: SupabaseClient, headers: HeadersInit): Promise<Response> {
  const url = new URL(req.url)
  const from = parseDate(url.searchParams.get('from')) ?? new Date(new Date().toISOString().slice(0, 10) + 'T00:00:00.000Z')
  const requestedDays = Number(url.searchParams.get('days') ?? 14)
  const days = Number.isFinite(requestedDays) ? Math.min(Math.max(Math.trunc(requestedDays), 1), 31) : 14
  const accessToken = await googleAccessToken()
  const availability = await availableSlots(supabase, from, days, accessToken)
  return json(availability, 200, headers)
}

async function handleBooking(req: Request, supabase: SupabaseClient, headers: HeadersInit): Promise<Response> {
  const payload = await req.json()
  if (cleanText(payload.website, 100)) return json({ ok: true }, 200, headers)
  const passedChallenge = await verifyTurnstile(cleanText(payload.turnstileToken, 2048), req.headers.get('cf-connecting-ip'))
  if (!passedChallenge) return json({ error: 'No se pudo validar la solicitud. Recarga la página e inténtalo de nuevo.' }, 400, headers)

  const name = cleanText(payload.name, 100)
  const email = cleanText(payload.email, 254).toLowerCase()
  const phone = cleanText(payload.phone, 30) || null
  const requestedStart = new Date(payload.startsAt)
  if (name.length < 2 || !validEmail(email) || (phone && phone.length < 7) || Number.isNaN(requestedStart.valueOf()) || payload.privacyAccepted !== true) {
    return json({ error: 'Revisa los datos obligatorios del formulario.' }, 400, headers)
  }

  const { settings } = await loadConfiguration(supabase)
  const requestedDate = new Date(requestedStart.toISOString().slice(0, 10) + 'T00:00:00.000Z')
  const googleToken = await googleAccessToken()
  const availability = await availableSlots(supabase, addUtcDays(requestedDate, -1), 3, googleToken)
  if (!availability.slots.includes(requestedStart.toISOString())) {
    return json({ error: 'Ese horario ya no está disponible. Elige otro hueco.' }, 409, headers)
  }
  const end = new Date(requestedStart.getTime() + settings.duration_minutes * 60_000)
  const holdExpiresAt = new Date(Date.now() + HOLD_MINUTES * 60_000)

  const { data: appointment, error: insertError } = await supabase.from('online_appointments').insert({
    patient_name: name,
    patient_email: email,
    patient_phone: phone,
    starts_at: requestedStart.toISOString(),
    ends_at: end.toISOString(),
    timezone: settings.timezone,
    status: 'awaiting_payment',
    hold_expires_at: holdExpiresAt.toISOString(),
    amount_cents: BOOKING_PRICE_CENTS,
    currency: 'eur',
    consent_at: new Date().toISOString(),
  }).select('id').single()

  if (insertError) {
    if (insertError.code === '23P01') return json({ error: 'Ese horario acaba de reservarse. Elige otro hueco.' }, 409, headers)
    throw new Error(`Appointment reservation failed: ${insertError.code}`)
  }

  try {
    const checkout = await createCheckoutSession(appointment.id, email, requestedStart)
    const { error: updateError } = await supabase.from('online_appointments').update({
      stripe_checkout_session_id: checkout.id,
      updated_at: new Date().toISOString(),
    }).eq('id', appointment.id)
    if (updateError) throw new Error('Checkout session persistence failed')
    return json({ ok: true, checkoutUrl: checkout.url, startsAt: requestedStart.toISOString() }, 201, headers)
  } catch (error) {
    await supabase.from('online_appointments').update({ status: 'failed', updated_at: new Date().toISOString() }).eq('id', appointment.id)
    throw error
  }
}

export default {
  async fetch(req: Request): Promise<Response> {
    const url = new URL(req.url)
    if (req.method === 'POST' && url.pathname.endsWith('/stripe-webhook')) {
      try {
        return await handleStripeWebhook(req, adminClient())
      } catch (error) {
        console.error(error instanceof Error ? error.message : 'Unknown Stripe webhook error')
        return new Response('Webhook processing failed', { status: 500 })
      }
    }
    const headers = corsHeaders(req)
    if (!headers) return new Response('Forbidden', { status: 403 })
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers })
    try {
      const supabase = adminClient()
      if (req.method === 'GET') return await handleAvailability(req, supabase, headers)
      if (req.method === 'POST') return await handleBooking(req, supabase, headers)
      return json({ error: 'Método no permitido.' }, 405, headers)
    } catch (error) {
      console.error(error instanceof Error ? error.message : 'Unknown booking error')
      return json({ error: 'No hemos podido completar la solicitud. Puedes pedir cita por WhatsApp.' }, 500, headers)
    }
  },
}
