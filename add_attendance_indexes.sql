-- Migration script to add composite indexes for attendance table
-- These indexes will significantly improve query performance for common patterns

-- Index for lookups by company, employee, and date (most common pattern)
CREATE INDEX IF NOT EXISTS idx_attendance_company_employee_date 
ON attendances(company_id, employee_id, attendance_date);

-- Index for date range queries by company
CREATE INDEX IF NOT EXISTS idx_attendance_company_date 
ON attendances(company_id, attendance_date);

-- Note: These indexes are already defined in the model, but if the table
-- was created before this change, you need to run this script to add them.



