import uuid
import psycopg2
import psycopg2.extras
from mef_mooc.config import DATABASE_HOST, DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD, DATABASE_PORT

class Database:
    def __init__(self):
        self.connection = psycopg2.connect(
            host=DATABASE_HOST,
            database=DATABASE_NAME,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            port=DATABASE_PORT
        )
        self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        self.connection.autocommit = True

    def execute(self, query, params=()):
        self.cursor.execute(query, params)
        
    def fetch(self, query, params=()):
        self.cursor.execute(query, params)
        result = self.cursor.fetchall()
        return [dict(row) for row in result]

    def fetch_one(self, query, params=()):
        self.cursor.execute(query, params)
        result = dict(self.cursor.fetchone()) if self.cursor.rowcount > 0 else None
        return result

    def __del__(self):
        self.cursor.close()
        self.connection.close()


create_tables = """

CREATE TABLE coordinator (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    surname VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(1023) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE department (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    coordinator_id INTEGER UNIQUE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT FK_DepartmentCoordinator FOREIGN KEY (coordinator_id) REFERENCES coordinator(id)
);

CREATE TABLE student (
    id SERIAL PRIMARY KEY,
    student_no VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    surname VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password VARCHAR(1023) NOT NULL, 
    department_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT FK_StudentDepartment FOREIGN KEY (department_id) REFERENCES department(id)
);

CREATE TABLE MEFcourse (
    id SERIAL PRIMARY KEY,
    course_code VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(255),
    semester VARCHAR(255) NOT NULL,
    credits INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    department_id INTEGER NOT NULL,
    coordinator_id INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (course_code, semester, name, department_id),
    CONSTRAINT FK_MEFcourseDepartment FOREIGN KEY (department_id) REFERENCES department(id),
    CONSTRAINT FK_MEFcourseCoordinator FOREIGN KEY (coordinator_id) REFERENCES coordinator(id)
);

CREATE TABLE enrollment (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    is_waiting BOOLEAN NOT NULL DEFAULT FALSE,
    is_pass BOOLEAN,
    pass_date TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (student_id, course_id),
    CONSTRAINT FK_EnrollmentStudent FOREIGN KEY (student_id) REFERENCES student(id),
    CONSTRAINT FK_EnrollmentCourse FOREIGN KEY (course_id) REFERENCES MEFcourse(id)
);

CREATE TABLE bundle (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    coordinator_id INTEGER,
    enrollment_id INTEGER NOT NULL,
    status VARCHAR(255) NOT NULL DEFAULT 'Waiting Bundle',
    comment VARCHAR(2047),
    CONSTRAINT FK_BundleCoordinator FOREIGN KEY (coordinator_id) REFERENCES coordinator(id),
    CONSTRAINT FK_BundleEnrollment FOREIGN KEY (enrollment_id) REFERENCES enrollment(id)
);

CREATE TABLE mooc (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    university VARCHAR(255),
    difficulty_level VARCHAR(255),
    course_ratio FLOAT,
    average_hours FLOAT,
    url VARCHAR(1023),
    description TEXT,
    skills_learned TEXT,
    specialization VARCHAR(255),
    specialization_course_order VARCHAR(255),
    specialization_url VARCHAR(1023),
    spezialization_description TEXT,
    course_language VARCHAR(255),
    course_id VARCHAR(255) UNIQUE,
    specialization_id VARCHAR(255),
    graded_peer_review INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE bundle_detail (
    id SERIAL PRIMARY KEY,
    bundle_id INTEGER NOT NULL,
    mooc_id INTEGER NOT NULL,
    certificate_url TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (bundle_id, mooc_id),
    CONSTRAINT FK_BundleDetailBundle FOREIGN KEY (bundle_id) REFERENCES bundle(id),
    CONSTRAINT FK_BundleDetailMooc FOREIGN KEY (mooc_id) REFERENCES mooc(id)
);

"""

db = Database()
