import { createClient } from 'npm:@supabase/supabase-js@2.95.0'

const LOCAL_ORIGIN = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/
const TIMEZONE = 'Europe/Madrid'
const DURATION_MINUTES = 50

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

function cors(origin: string): Record<string, string> {
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Headers': 'content-type, x-demo-access',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    'Vary': 'Origin',
  }
}

function clean(value: unknown, max: number): string {
  return typeof value === 'string' ? value.trim().replace(/\s+/g, ' ').slice(0, max) : ''
}

function validEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) && value.length <= 254
}

function validSlot(start: Date): boolean {
  const now = Date.now()
  if (start.getTime() < now + 72 * 3_600_000 || start.getTime() > now + 60 * 86_400_000) return false
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: TIMEZONE,
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(start)
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  const hour = Number(values.hour)
  if (Number(values.minute) !== 0) return false
  if (values.weekday === 'Mon' || values.weekday === 'Wed') return hour >= 16 && hour <= 19
  if (values.weekday === 'Tue' || values.weekday === 'Thu') return hour >= 9 && hour <= 12
  return false
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

async function createGoogleEvent(
  token: string,
  reference: string,
  name: string,
  email: string,
  start: Date,
  end: Date,
) {
  const calendarId = requiredEnv('GOOGLE_CALENDAR_ID')
  const eventId = `fisio${reference.replaceAll('-', '')}`
  const baseUrl = `https://www.googleapis.com/calendar/v3/calendars/${encodeURIComponent(calendarId)}/events`
  const response = await fetch(`${baseUrl}?conferenceDataVersion=1&sendUpdates=all`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      id: eventId,
      summary: 'Consulta online · FisioLógico',
      description: 'Consulta online con Fran. Accede a la videollamada desde el enlace de Google Meet incluido en esta invitación.',
      start: { dateTime: start.toISOString(), timeZone: TIMEZONE },
      end: { dateTime: end.toISOString(), timeZone: TIMEZONE },
      attendees: [{ email, displayName: name }],
      conferenceData: {
        createRequest: {
          requestId: reference,
          conferenceSolutionKey: { type: 'hangoutsMeet' },
        },
      },
      reminders: {
        useDefault: false,
        overrides: [{ method: 'email', minutes: 1440 }, { method: 'popup', minutes: 15 }],
      },
      extendedProperties: { private: { fisiologicoAppointmentId: reference, source: 'private-preview' } },
    }),
  })
  const event = await response.json()
  if (response.status === 409) {
    const existing = await fetch(`${baseUrl}/${eventId}`, { headers: { Authorization: `Bearer ${token}` } })
    if (existing.ok) return await existing.json()
  }
  if (!response.ok) throw new Error(`Google event creation failed (${response.status}): ${event.error?.message ?? 'unknown'}`)
  return event
}

Deno.serve(async (req) => {
  const origin = req.headers.get('origin') ?? ''
  if (!LOCAL_ORIGIN.test(origin)) return new Response('Forbidden', { status: 403 })
  const headers = cors(origin)
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers })
  if (req.method !== 'POST') return Response.json({ error: 'Método no permitido.' }, { status: 405, headers })
  if (req.headers.get('x-demo-access') !== requiredEnv('DEMO_CONFIRM_ACCESS')) {
    return Response.json({ error: 'Acceso no autorizado.' }, { status: 401, headers })
  }

  try {
    const payload = await req.json()
    const reference = clean(payload.reference, 36).toLowerCase()
    const name = clean(payload.name, 100)
    const email = clean(payload.email, 254).toLowerCase()
    const start = new Date(payload.startsAt)
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(reference) ||
        name.length < 2 || !validEmail(email) || Number.isNaN(start.valueOf()) || !validSlot(start)) {
      return Response.json({ error: 'Los datos de la reserva no son válidos.' }, { status: 400, headers })
    }

    const supabase = createClient(requiredEnv('SUPABASE_URL'), secretKey(), {
      auth: { persistSession: false, autoRefreshToken: false },
    })
    const { data: existing } = await supabase
      .from('online_appointments')
      .select('status, meet_url, google_event_url')
      .eq('id', reference)
      .maybeSingle()
    if (existing?.status === 'confirmed') {
      return Response.json({ ok: true, meetUrl: existing.meet_url, calendarUrl: existing.google_event_url }, { headers })
    }

    const end = new Date(start.getTime() + DURATION_MINUTES * 60_000)
    if (!existing) {
      const { error: insertError } = await supabase.from('online_appointments').insert({
        id: reference,
        patient_name: name,
        patient_email: email,
        starts_at: start.toISOString(),
        ends_at: end.toISOString(),
        timezone: TIMEZONE,
        status: 'payment_received',
        hold_expires_at: new Date(Date.now() + 24 * 3_600_000).toISOString(),
        amount_cents: 7000,
        currency: 'eur',
        consent_at: new Date().toISOString(),
      })
      if (insertError?.code === '23P01') {
        return Response.json({ error: 'Ese horario ya no está disponible.' }, { status: 409, headers })
      }
      if (insertError) throw new Error(`Appointment insert failed: ${insertError.code}`)
    }

    const event = await createGoogleEvent(await googleAccessToken(), reference, name, email, start, end)
    const { error: updateError } = await supabase.from('online_appointments').update({
      status: 'confirmed',
      google_event_id: event.id,
      google_event_url: event.htmlLink ?? null,
      meet_url: event.hangoutLink ?? null,
      updated_at: new Date().toISOString(),
    }).eq('id', reference)
    if (updateError) throw new Error(`Appointment update failed: ${updateError.code}`)

    return Response.json({ ok: true, meetUrl: event.hangoutLink ?? null, calendarUrl: event.htmlLink ?? null }, { headers })
  } catch (error) {
    console.error(error instanceof Error ? error.message : 'Unknown confirmation error')
    return Response.json({ error: 'No hemos podido confirmar la cita. Contacta con FisioLógico por email.' }, { status: 500, headers })
  }
})
