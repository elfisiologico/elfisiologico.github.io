import assert from 'node:assert/strict'
import test from 'node:test'
import { addUtcDays, overlaps, parseDate, zonedDateTimeToUtc } from '../supabase/functions/_shared/time.ts'

test('convierte el horario de invierno de Madrid a UTC', () => {
  assert.equal(zonedDateTimeToUtc('2026-01-20', '09:00', 'Europe/Madrid').toISOString(), '2026-01-20T08:00:00.000Z')
})

test('convierte el horario de verano de Madrid a UTC', () => {
  assert.equal(zonedDateTimeToUtc('2026-07-20', '09:00', 'Europe/Madrid').toISOString(), '2026-07-20T07:00:00.000Z')
})

test('mantiene la fecha civil al avanzar días', () => {
  assert.equal(addUtcDays(new Date('2026-07-31T00:00:00.000Z'), 1).toISOString(), '2026-08-01T00:00:00.000Z')
})

test('rechaza fechas imposibles o mal formadas', () => {
  assert.equal(parseDate('2026-02-29'), null)
  assert.equal(parseDate('20-02-01'), null)
  assert.equal(parseDate('2026-02-28')?.toISOString(), '2026-02-28T00:00:00.000Z')
})

test('trata los intervalos como [inicio, fin)', () => {
  const busy = { start: '2026-07-20T08:00:00.000Z', end: '2026-07-20T09:00:00.000Z' }
  assert.equal(overlaps(new Date('2026-07-20T07:30:00.000Z'), new Date('2026-07-20T08:30:00.000Z'), busy), true)
  assert.equal(overlaps(new Date('2026-07-20T09:00:00.000Z'), new Date('2026-07-20T10:00:00.000Z'), busy), false)
})
