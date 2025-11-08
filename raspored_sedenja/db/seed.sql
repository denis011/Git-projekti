-- Seed: 1 building, 1 floor, 1 zone, 10 seats
INSERT INTO building (name) VALUES ('HQ') ON CONFLICT DO NOTHING;
INSERT INTO floor (building_id, name) 
SELECT id, 'Floor 1' FROM building WHERE name='HQ' 
ON CONFLICT DO NOTHING;

INSERT INTO zone (floor_id, name, type, capacity)
SELECT f.id, 'Open Space', 'open', 10
FROM floor f JOIN building b ON f.building_id=b.id
WHERE b.name='HQ' AND f.name='Floor 1'
ON CONFLICT DO NOTHING;

DO $$
DECLARE
  zid INT;
  i INT;
BEGIN
  SELECT z.id INTO zid FROM zone z JOIN floor f ON z.floor_id=f.id 
  JOIN building b ON f.building_id=b.id
  WHERE b.name='HQ' AND f.name='Floor 1' AND z.name='Open Space' LIMIT 1;

  IF zid IS NOT NULL THEN
    FOR i IN 1..10 LOOP
      BEGIN
        INSERT INTO seat(zone_id, code) VALUES (zid, 'S-'||i);
      EXCEPTION WHEN unique_violation THEN
        CONTINUE;
      END;
    END LOOP;
  END IF;
END$$;

-- Admin user (local auth); change password after first login.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM app_user WHERE upn='admin') THEN
    INSERT INTO app_user (upn, name, dept, roles, password_hash)
    VALUES ('admin', 'System Administrator', 'IT', ARRAY['admin'], '$2b$12$QMP6JNZgZPXjzNThuJrWv.1xjs9VEZTdiQJIU.98/VeyHBVnADylK');
  END IF;
END$$;
