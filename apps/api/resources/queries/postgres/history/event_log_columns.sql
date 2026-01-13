SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'event_log'
ORDER BY ordinal_position
