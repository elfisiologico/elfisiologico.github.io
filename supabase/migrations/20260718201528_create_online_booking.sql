create table if not exists public.booking_settings (
  id boolean primary key default true check (id),
  active boolean not null default false,
  timezone text not null default 'Europe/Madrid',
  duration_minutes smallint not null default 50 check (duration_minutes between 15 and 180),
  slot_interval_minutes smallint not null default 30 check (slot_interval_minutes between 5 and 180),
  min_notice_hours smallint not null default 24 check (min_notice_hours between 0 and 720),
  max_days_ahead smallint not null default 60 check (max_days_ahead between 1 and 365),
  updated_at timestamptz not null default now()
);

create table if not exists public.booking_availability (
  id bigint generated always as identity primary key,
  weekday smallint not null check (weekday between 1 and 7),
  starts_at time not null,
  ends_at time not null,
  active boolean not null default true,
  check (starts_at < ends_at),
  unique (weekday, starts_at, ends_at)
);

create table if not exists public.online_appointments (
  id uuid primary key default gen_random_uuid(),
  patient_name text not null check (char_length(patient_name) between 2 and 100),
  patient_email text not null check (char_length(patient_email) between 5 and 254),
  patient_phone text check (patient_phone is null or char_length(patient_phone) between 7 and 30),
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  timezone text not null default 'Europe/Madrid',
  status text not null default 'awaiting_payment' check (status in ('awaiting_payment', 'payment_received', 'confirmed', 'expired', 'cancelled', 'refunded', 'failed')),
  hold_expires_at timestamptz not null,
  amount_cents integer not null default 7000 check (amount_cents > 0),
  currency text not null default 'eur' check (currency = lower(currency) and char_length(currency) = 3),
  stripe_checkout_session_id text unique,
  stripe_payment_intent_id text unique,
  google_event_id text unique,
  google_event_url text,
  meet_url text,
  consent_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (starts_at < ends_at)
);

alter table public.booking_settings enable row level security;
alter table public.booking_availability enable row level security;
alter table public.online_appointments enable row level security;

revoke all on table public.booking_settings from anon, authenticated;
revoke all on table public.booking_availability from anon, authenticated;
revoke all on table public.online_appointments from anon, authenticated;
revoke all on sequence public.booking_availability_id_seq from anon, authenticated;

grant select, insert, update, delete on table public.booking_settings to service_role;
grant select, insert, update, delete on table public.booking_availability to service_role;
grant select, insert, update, delete on table public.online_appointments to service_role;
grant usage, select on sequence public.booking_availability_id_seq to service_role;

alter table public.online_appointments
  drop constraint if exists online_appointments_no_overlap;

alter table public.online_appointments
  add constraint online_appointments_no_overlap
  exclude using gist (
    tstzrange(starts_at, ends_at, '[)') with &&
  ) where (status in ('awaiting_payment', 'payment_received', 'confirmed'));

create index if not exists online_appointments_starts_at_idx
  on public.online_appointments (starts_at);

comment on table public.online_appointments is
  'Administrative booking data only. Do not store symptoms or clinical notes here.';

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

insert into public.booking_availability (weekday, starts_at, ends_at, active)
values
  (1, '16:00', '20:00', false),
  (2, '09:00', '13:00', false),
  (3, '16:00', '20:00', false),
  (4, '09:00', '13:00', false)
on conflict (weekday, starts_at, ends_at) do update set active = excluded.active;
