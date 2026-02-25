-- Migration: Add is_tester column to users table
-- Run this on the production database to add tester support

-- Add is_tester column if it doesn't exist
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'is_tester'
    ) THEN
        ALTER TABLE users ADD COLUMN is_tester BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Column is_tester added to users table';
    ELSE
        RAISE NOTICE 'Column is_tester already exists in users table';
    END IF;
END $$;

-- Verify the column was added
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name = 'is_tester';
