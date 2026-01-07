-- Drop existing tables if they exist
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS flagged_activities CASCADE;
DROP TABLE IF EXISTS votes CASCADE;
DROP TABLE IF EXISTS candidates CASCADE;
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS elections CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS system_configuration CASCADE;
DROP TABLE IF EXISTS ml_model_configuration CASCADE;
-- System Configuration Table
CREATE TABLE system_configuration (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    config_type VARCHAR(50),
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- ML Model Configuration Table
CREATE TABLE ml_model_configuration (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50),
    is_active BOOLEAN DEFAULT FALSE,
    parameters JSONB,
    threshold_config JSONB,
    feature_weights JSONB,
    training_date TIMESTAMP,
    accuracy_metrics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Users Table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    voter_id VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'voter',
    phone_number VARCHAR(20),
    date_of_birth DATE,
    address TEXT,
    custom_fields JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Elections Table
CREATE TABLE elections (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    allow_multiple_positions BOOLEAN DEFAULT TRUE,
    require_voter_verification BOOLEAN DEFAULT TRUE,
    max_votes_per_position INTEGER DEFAULT 1,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Positions Table
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    election_id INTEGER REFERENCES elections(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    max_candidates_to_select INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Candidates Table
CREATE TABLE candidates (
    id SERIAL PRIMARY KEY,
    position_id INTEGER REFERENCES positions(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    party VARCHAR(100),
    biography TEXT,
    manifesto TEXT,
    image_url VARCHAR(255),
    video_url VARCHAR(255),
    social_media JSONB,
    custom_fields JSONB,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Votes Table
CREATE TABLE votes (
    id SERIAL PRIMARY KEY,
    election_id INTEGER REFERENCES elections(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    candidate_id INTEGER REFERENCES candidates(id) ON DELETE CASCADE,
    position_id INTEGER REFERENCES positions(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(50),
    device_fingerprint VARCHAR(255),
    session_duration INTEGER,
    mouse_movements INTEGER,
    keystroke_patterns INTEGER,
    user_agent VARCHAR(255),
    geo_location JSONB,
    is_flagged BOOLEAN DEFAULT FALSE,
    risk_level VARCHAR(20),
    anomaly_score FLOAT,
    detection_features JSONB
);
-- Flagged Activities Table
CREATE TABLE flagged_activities (
    id SERIAL PRIMARY KEY,
    vote_id INTEGER REFERENCES votes(id),
    voter_id VARCHAR(50),
    election_id INTEGER REFERENCES elections(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    risk_level VARCHAR(20),
    anomaly_score FLOAT,
    reasons JSONB,
    metadata JSONB,
    ip_address VARCHAR(50),
    resolved BOOLEAN DEFAULT FALSE,
    resolved_by INTEGER REFERENCES users(id),
    resolved_at TIMESTAMP,
    resolution_notes TEXT
);
-- Audit Logs Table
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSONB,
    ip_address VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Create Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_voter_id ON users(voter_id);
CREATE INDEX idx_elections_active ON elections(is_active);
CREATE INDEX idx_votes_user ON votes(user_id);
CREATE INDEX idx_votes_election ON votes(election_id);
CREATE INDEX idx_votes_candidate ON votes(candidate_id);
CREATE INDEX idx_votes_flagged ON votes(is_flagged);
CREATE INDEX idx_flagged_activities_election ON flagged_activities(election_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
-- Insert Default System Configuration
INSERT INTO system_configuration (
        config_key,
        config_value,
        config_type,
        description
    )
VALUES (
        'app_name',
        'Intelligent Voting System',
        'string',
        'Application name'
    ),
    (
        'allow_registration',
        'true',
        'boolean',
        'Allow new user registration'
    ),
    (
        'require_email_verification',
        'false',
        'boolean',
        'Require email verification'
    ),
    (
        'max_login_attempts',
        '5',
        'integer',
        'Maximum login attempts before lockout'
    ),
    (
        'session_timeout',
        '7200',
        'integer',
        'Session timeout in seconds'
    );
-- Insert Default ML Configuration
INSERT INTO ml_model_configuration (
        model_name,
        model_type,
        is_active,
        parameters,
        threshold_config,
        feature_weights
    )
VALUES (
        'Default Fraud Detector',
        'isolation_forest',
        true,
        '{"features": ["session_duration", "mouse_movements", "keystroke_patterns", "hour_of_day", "votes_from_ip", "time_since_page_load"], "contamination": 0.1, "n_estimators": 100}'::jsonb,
        '{"fast_voting": 5000, "low_interaction": 5, "unusual_hours_start": 2, "unusual_hours_end": 5, "high_risk_score": 0.75, "medium_risk_score": 0.45}'::jsonb,
        '{"session_duration": 0.25, "mouse_movements": 0.20, "keystroke_patterns": 0.15, "hour_of_day": 0.15, "votes_from_ip": 0.25, "time_since_page_load": 0.10}'::jsonb
    );
-- Create Admin User (password: admin123)
INSERT INTO users (
        voter_id,
        full_name,
        email,
        password_hash,
        role,
        is_active,
        is_verified
    )
VALUES (
        'ADMIN001',
        'System Administrator',
        'admin@voting.com',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5zzDKJ/cDKMgy',
        'admin',
        true,
        true
    );
-- Create Sample Voter (password: password123)
INSERT INTO users (
        voter_id,
        full_name,
        email,
        password_hash,
        role,
        is_active,
        is_verified
    )
VALUES (
        'VID001',
        'John Doe',
        'voter@test.com',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5zzDKJ/cDKMgy',
        'voter',
        true,
        true
    );
-- Create Sample Election
INSERT INTO elections (
        title,
        description,
        start_date,
        end_date,
        is_active,
        created_by
    )
VALUES (
        'Student Union Election 2026',
        'Annual student union executive elections',
        '2026-01-20 08:00:00',
        '2026-01-25 18:00:00',
        true,
        1
    );
-- Create Sample Positions
INSERT INTO positions (election_id, title, description, display_order)
VALUES (1, 'President', 'Student Union President', 1),
    (
        1,
        'Vice President',
        'Student Union Vice President',
        2
    ),
    (1, 'Secretary', 'Student Union Secretary', 3),
    (1, 'Treasurer', 'Student Union Treasurer', 4);
-- Create Sample Candidates
INSERT INTO candidates (
        position_id,
        name,
        party,
        biography,
        image_url,
        display_order
    )
VALUES (
        1,
        'Sarah Johnson',
        'Progressive Alliance',
        'Experienced leader with vision for change',
        '👩‍💼',
        1
    ),
    (
        1,
        'Michael Chen',
        'Reform Party',
        'Committed to transparency and innovation',
        '👨‍💼',
        2
    ),
    (
        2,
        'Amara Okafor',
        'Unity Front',
        'Dedicated to student welfare',
        '👩‍⚖️',
        1
    ),
    (
        2,
        'David Martinez',
        'Change Coalition',
        'Advocate for student rights',
        '👨‍🏫',
        2
    ),
    (
        3,
        'Emily Brown',
        'Progressive Alliance',
        'Detail-oriented administrator',
        '👩‍💻',
        1
    ),
    (
        3,
        'James Wilson',
        'Reform Party',
        'Organized and efficient',
        '👨‍💻',
        2
    ),
    (
        4,
        'Lisa Anderson',
        'Unity Front',
        'Financial management expert',
        '👩‍💼',
        1
    ),
    (
        4,
        'Robert Taylor',
        'Change Coalition',
        'Experienced in budget planning',
        '👨‍💼',
        2
    );
-- Grant all privileges to voting_user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO voting_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO voting_user;