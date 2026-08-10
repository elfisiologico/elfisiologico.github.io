-- Revisa estos valores antes de ejecutarlos en producción.
insert into public.booking_settings (
  id,
  active,
  timezone,
  duration_minutes,
  slot_interval_minutes,
  min_notice_hours,
  max_days_ahead
) values (
  true,
  false,
  'Europe/Madrid',
  50,
  60,
  72,
  60
)
on conflict (id) do update set
  active = excluded.active,
  timezone = excluded.timezone,
  duration_minutes = excluded.duration_minutes,
  slot_interval_minutes = excluded.slot_interval_minutes,
  min_notice_hours = excluded.min_notice_hours,
  max_days_ahead = excluded.max_days_ahead,
  updated_at = now();

-- Horario acordado con Fran. Permanece inactivo hasta completar la puesta en producción.
insert into public.booking_availability (weekday, starts_at, ends_at, active)
values
  (1, '16:00', '20:00', false),
  (2, '09:00', '13:00', false),
  (3, '16:00', '20:00', false),
  (4, '09:00', '13:00', false)
on conflict (weekday, starts_at, ends_at) do update set active = excluded.active;
