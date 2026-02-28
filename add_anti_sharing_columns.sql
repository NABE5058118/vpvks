-- Migration: Add anti-sharing fields to users table
-- Run this on the production database to add device fingerprint tracking

-- Add anti-sharing columns if they don't exist
DO $$
BEGIN
    -- last_connected_ip
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users'
        AND column_name = 'last_connected_ip'
    ) THEN
        ALTER TABLE users ADD COLUMN last_connected_ip VARCHAR(45);
        RAISE NOTICE 'Column last_connected_ip added to users table';
    END IF;
    
    -- last_connected_user_agent
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users'
        AND column_name = 'last_connected_user_agent'
    ) THEN
        ALTER TABLE users ADD COLUMN last_connected_user_agent VARCHAR(500);
        RAISE NOTICE 'Column last_connected_user_agent added to users table';
    END IF;
    
    -- connection_count
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users'
        AND column_name = 'connection_count'
    ) THEN
        ALTER TABLE users ADD COLUMN connection_count INTEGER DEFAULT 0;
        RAISE NOTICE 'Column connection_count added to users table';
    END IF;
    
    -- suspicious_activity
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users'
        AND column_name = 'suspicious_activity'
    ) THEN
        ALTER TABLE users ADD COLUMN suspicious_activity BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Column suspicious_activity added to users table';
    END IF;
END $$;

-- Verify the columns were added
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'users'
AND column_name IN ('last_connected_ip', 'last_connected_user_agent', 'connection_count', 'suspicious_activity');
