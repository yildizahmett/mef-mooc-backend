import random
import string
from flask import request, jsonify
from flask_jwt_extended import create_access_token, get_jwt, jwt_required

from scripts.util import *
from scripts.auth import student_auth, coordinator_auth, admin_auth
from scripts.init import app, jwt, bcrypt, db

#=======================================================================================================
#=======================================  GENERAL  =====================================================

@app.route("/all-departments", methods=['GET'])
def all_departments():
    try:
        departments = db.fetch("SELECT * FROM department")
        return {"departments": departments}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/all-coordinators", methods=['GET'])
def all_coordinators():
    try:
        coordinators = db.fetch("SELECT id, CONCAT(name, ' ', surname) as name FROM coordinator")
        return {"coordinators": coordinators}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

#=======================================================================================================
#=======================================  STUDENT  =====================================================

@app.route("/student/register", methods=['POST'])
def student_register():
    try:
        data = request.get_json()
        student_no = data['student_no']
        name = data['name']
        surname = data['surname']
        email = data['email']
        password = data['password']
        department_id = data['department_id']

        student = db.fetch_one("SELECT * FROM student WHERE student_no = %s LIMIT 1", (student_no,))
        if student:
            return {"message": "Student already exists"}, 400

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        db.execute("INSERT INTO student (student_no, name, surname, email, password, department_id) VALUES (%s, %s, %s, %s, %s, %s)", (student_no, name, surname, email, hashed_password, department_id))
        return {"message": "Student created successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/login", methods=['POST'])
def student_login():
    try:
        data = request.get_json()
        student_no = data['student_no']
        password = data['password']

        student = db.fetch_one("SELECT * FROM student WHERE student_no = %s LIMIT 1", (student_no,))
        if not student:
            return {"message": "Invalid credentials"}, 401

        if not bcrypt.check_password_hash(student['password'], password):
            return {"message": "Invalid credentials"}, 401

        token_identity = {
            'type': 'student',
            'id': student['id']
        }

        access_token = create_access_token(identity=token_identity)
        return {"access_token": access_token}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/courses", methods=['GET'])
@student_auth()
def student_courses():
    try:
        student_id = get_jwt()['sub']['id']
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))

        if not student:
            return {"message": "Student not found"}, 404

        courses = db.fetch(
            """SELECT id, name, course_code
               FROM MEFcourse
               WHERE department_id = %s and is_active = True
            """,
            (student['department_id'],)
        )
        return {"courses": courses}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/enroll", methods=['POST'])
@student_auth()
def student_enroll():
    try:
        data = request.get_json()
        student_id = get_jwt()['sub']['id']
        course_id = data['course_id']

        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))
        if not student:
            return {"message": "Student not found"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s and is_active = True LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        if course['department_id'] != student['department_id']:
            return {"message": "You cannot enroll in this course"}, 400

        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE student_id = %s and course_id = %s LIMIT 1", (student_id, course_id))
        if enrollment:
            return {"message": "You are already enrolled in this course"}, 400

        db.execute("INSERT INTO enrollment (student_id, course_id) VALUES (%s, %s)", (student_id, course_id))
        return {"message": "Enrolled successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/enrollments", methods=['GET'])
@student_auth()
def student_enrollments():
    try:
        student_id = get_jwt()['sub']['id']
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))

        if not student:
            return {"message": "Student not found"}, 404

        enrollments = db.fetch(
            """SELECT e.id as enrolment_id, c.id as course_id, c.name, c.course_code
               FROM enrollment e
               INNER JOIN MEFcourse c ON c.id = e.course_id
               WHERE e.student_id = %s and c.is_active = True
            """,
            (student_id,)
        )
        return {"enrollments": enrollments}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/enrollments/<int:course_id>/bundles", methods=['GET'])
@student_auth()
def student_enrollment_bundles(course_id):
    try:
        student_id = get_jwt()['sub']['id']
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))

        if not student:
            return {"message": "Student not found"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s and is_active = True LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        if course['department_id'] != student['department_id']:
            return {"message": "You cannot view this course"}, 400

        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE student_id = %s and course_id = %s LIMIT 1", (student_id, course_id))
        if not enrollment:
            return {"message": "You are not enrolled in this course"}, 400

        bundles = db.fetch(
            """SELECT b.id as bundle_id, b.created_at, b.status as bundle_status, m.name, m.url
               FROM bundle b
               INNER JOIN bundle_detail bd ON bd.bundle_id = b.id
               INNER JOIN mooc m ON m.id = bd.mooc_id
               WHERE b.enrollment_id = %s
            """,
            (enrollment["id"],)
        )
        return {"bundles": bundles}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/moocs", methods=['GET'])
@student_auth()
def student_moocs():
    try:
        student_id = get_jwt()['sub']['id']
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))

        if not student:
            return {"message": "Student not found"}, 404

        moocs = db.fetch("SELECT id, platform, name, url FROM mooc WHERE is_active = True")
        return {"moocs": moocs}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/enrollments/<int:course_id>/create-bundle", methods=['POST'])
@student_auth()
def student_create_bundle(course_id):
    try:
        student_id = get_jwt()['sub']['id']
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))

        if not student:
            return {"message": "Student not found"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s and is_active = True LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        if course['department_id'] != student['department_id']:
            return {"message": "You cannot view this course"}, 400

        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE student_id = %s and course_id = %s LIMIT 1", (student_id, course_id))
        if not enrollment:
            return {"message": "You are not enrolled in this course"}, 400

        bundles = db.fetch(
            """
            SELECT * FROM bundle WHERE enrollment_id = %s
                                 AND (status = 'Waiting Bundle' OR status = 'Waiting Certificates'
                                 OR status = 'Rejected Certificates' OR status = 'Accepted Certificates'
                                 OR status = 'Waiting Approval')
            """,
            (enrollment["id"],)
        )
        if len(bundles) != 0:
            return {"message": "You cannot create a new bundle because you have waiting or accepting bundles"}, 400

        data = request.get_json()
        mooc_ids = data['mooc_ids']

        moocs = db.fetch("SELECT * FROM mooc WHERE id IN %s and is_active = True", (tuple(mooc_ids),))
        if len(moocs) != len(mooc_ids):
            return {"message": "Invalid mooc ids"}, 400
        
        try:
            bundle = db.execute("INSERT INTO bundle (enrollment_id) VALUES (%s)", (enrollment['id'],))
            bundle_id = db.fetch_one("SELECT id FROM bundle WHERE enrollment_id = %s ORDER BY id DESC LIMIT 1", (enrollment['id'],))["id"]
            for mooc in mooc_ids:
                db.execute("INSERT INTO bundle_detail (bundle_id, mooc_id) VALUES (%s, %s)", (bundle_id, mooc))

        # TODO: ROllback
        except Exception as e:
            print(e)
            return {"message": "An error occured"}, 500

        return {"message": "Bundle created successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/enrollments/<int:course_id>/bundles/<int:bundle_id>", methods=['GET'])
@student_auth()
def student_bundle(course_id, bundle_id):
    try:
        student_id = get_jwt()['sub']['id']
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))

        if not student:
            return {"message": "Student not found"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s and is_active = True LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        if course['department_id'] != student['department_id']:
            return {"message": "You cannot view this course"}, 400

        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE student_id = %s and course_id = %s LIMIT 1", (student_id, course_id))
        if not enrollment:
            return {"message": "You are not enrolled in this course"}, 400

        bundles = db.fetch(
            """
            SELECT bd.id as bundle_detail_id, m.id as mooc_id, m.name as mooc_name, certificate_url
            FROM bundle_detail bd
            INNER JOIN mooc m ON m.id = bd.mooc_id
            WHERE bd.bundle_id = %s
            """,
            (bundle_id,)
        )
        return {"bundle": bundles}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/enrollments/<int:course_id>/bundles/<int:bundle_id>/certificate", methods=['POST'])
@student_auth()
def student_create_certificate(course_id, bundle_id):
    try:
        student_id = get_jwt()['sub']['id']
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))

        if not student:
            return {"message": "Student not found"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s and is_active = True LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        if course['department_id'] != student['department_id']:
            return {"message": "You cannot view this course"}, 400

        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE student_id = %s and course_id = %s LIMIT 1", (student_id, course_id))
        if not enrollment:
            return {"message": "You are not enrolled in this course"}, 400

        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s and enrollment_id = %s LIMIT 1", (bundle_id, enrollment['id']))
        if not bundle:
            return {"message": "Bundle not found"}, 404

        if bundle['status'] != 'Waiting Certificates':
            return {"message": "You cannot upload certificates for this bundle"}, 400

        data = request.get_json()
        certificate_url = data['certificate_url']
        bundle_detail_id = data['bundle_detail_id']

        db.execute("UPDATE bundle_detail SET certificate_url = %s WHERE id = %s", (certificate_url, bundle_detail_id))

        return {"message": "Certificate created successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/enrollments/<int:course_id>/bundles/<int:bundle_id>/complete", methods=['POST'])
@student_auth()
def student_complete_bundle(course_id, bundle_id):
    try:
        student_id = get_jwt()['sub']['id']
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))

        if not student:
            return {"message": "Student not found"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s and is_active = True LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        if course['department_id'] != student['department_id']:
            return {"message": "You cannot view this course"}, 400

        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE student_id = %s and course_id = %s LIMIT 1", (student_id, course_id))
        if not enrollment:
            return {"message": "You are not enrolled in this course"}, 400

        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s and enrollment_id = %s LIMIT 1", (bundle_id, enrollment['id']))
        if not bundle:
            return {"message": "Bundle not found"}, 404

        if bundle['status'] != 'Waiting Certificates':
            return {"message": "You cannot complete this bundle"}, 400

        bundle_details = db.fetch("SELECT * FROM bundle_detail WHERE bundle_id = %s", (bundle_id,))
        for bundle_detail in bundle_details:
            if not bundle_detail['certificate_url']:
                return {"message": "You cannot complete this bundle"}, 400

        db.execute("UPDATE bundle SET status = 'Waiting Approval' WHERE id = %s", (bundle_id,))

        return {"message": "Bundle completed successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

#=======================================================================================================
#========================================== COORDINATOR ================================================

@app.route("/coordinator/login", methods=['POST'])
def coordinator_login():
    try:
        data = request.get_json()
        email = data['email']
        password = data['password']

        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE email = %s and is_active = True LIMIT 1", (email,))
        if not coordinator:
            return {"message": "Invalid credentials or coordinator disabled"}, 401

        if not bcrypt.check_password_hash(coordinator['password'], password):
            return {"message": "Invalid credentials or coordinator disabled"}, 401

        token_identity = {
            'type': 'coordinator',
            'id': coordinator['id']
        }

        access_token = create_access_token(identity=token_identity)
        return {"access_token": access_token, "coordinator_name": coordinator["name"] + " " + coordinator["surname"]}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/coordinator/possible-semesters", methods=['GET'])
@coordinator_auth()
def coordinator_possible_semesters():
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        return {"semesters": SEMESTERS}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/coordinator/add-course", methods=['POST'])
@coordinator_auth()
def coordinator_add_course():
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator['id'],))
        if not department:
            return {"message": "Department not found or department disabled"}, 404

        data = request.get_json()
        course_code = data['course_code']
        name = data['name']
        type = data['type']
        semester = data['semester']
        credits = data['credits']

        db.execute("INSERT INTO MEFcourse (course_code, name, type, semester, credits, department_id, coordinator_id) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
                    (course_code, name, type, semester, credits, department['id'], coordinator_id))

        return {"message": "Course added successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/coordinator/course/<int:course_id>/passive", methods=['POST'])
@coordinator_auth()
def coordinator_passive_course(course_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s and is_active = True LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator['id'],))
        if not department:
            return {"message": "Department not found or department disabled"}, 404

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        db.execute("UPDATE MEFcourse SET is_active = False WHERE id = %s", (course_id,))

        return {"message": "Course passived successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/coordinator/active-courses", methods=['GET'])
@coordinator_auth()
def coordinator_active_courses():
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator['id'],))
        if not department:
            return {"message": "Department not found or department disabled"}, 404

        courses = db.fetch("SELECT * FROM MEFcourse WHERE department_id = %s and is_active = True", (department['id'],))
        return {"courses": courses}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/coordinator/inactive-courses", methods=['GET'])
@coordinator_auth()
def coordinator_inactive_courses():
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator['id'],))
        if not department:
            return {"message": "Department not found or department disabled"}, 404

        courses = db.fetch("SELECT * FROM MEFcourse WHERE department_id = %s and is_active = False", (department['id'],))
        return {"courses": courses}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/coordinator/course/<int:course_id>/students", methods=['GET'])
@coordinator_auth()
def coordinator_course(course_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        students = db.fetch("""
                            SELECT student.id, student.name, student.surname, student.email, student.student_no
                            FROM student
                            INNER JOIN enrollment ON student.id = enrollment.student_id
                            WHERE enrollment.course_id = %s
        """, (course_id,))

        return {"students": students}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/coordinator/course/<int:course_id>/<status>", methods=['GET'])
@coordinator_auth()
def coordinator_course_waiting_bundles(course_id, status):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        hashed_status = BUNDLE_STATUS.get(status)

        if not hashed_status:
            return {"message": "Status not found"}, 404

        # TODO: Get total bundle hours
        bundles = db.fetch("""
                            SELECT s.id as student_id, s.name as student_name, s.surname as student_surname, s.email as student_email, 
                                   s.student_no, b.id as bundle_id, b.created_at as bundle_created_at, m.name as mooc_name, e.pass_date,
                                   m.url as mooc_url, bd.certificate_url, CONCAT(c.name, ' ', c.surname) as coordinator_name
                            FROM student s
                            INNER JOIN enrollment e ON s.id = e.student_id
                            INNER JOIN bundle b ON e.id = b.enrollment_id
                            INNER JOIN bundle_detail bd ON b.id = bd.bundle_id
                            INNER JOIN mooc m ON bd.mooc_id = m.id
                            LEFT JOIN coordinator c ON b.coordinator_id = c.id
                            WHERE b.status = %s and e.course_id = %s
                            ORDER BY b.created_at DESC
        """, (hashed_status, course_id,))

        return {"bundles": bundles, "is_active": course["is_active"]}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/coordinator/course/<int:course_id>/bundle/<int:bundle_id>/approve-bundle", methods=['POST'])
@coordinator_auth()
def coordinator_approve_bundle(course_id, bundle_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s LIMIT 1", (bundle_id,))
        if not bundle:
            return {"message": "Bundle not found"}, 404

        if bundle['status'] != BUNDLE_STATUS['waiting-bundles']:
            return {"message": "Bundle is not waiting for approval"}, 400

        db.execute("UPDATE bundle SET status = %s, coordinator_id = %s WHERE id = %s", (BUNDLE_STATUS['waiting-certificates'], coordinator["id"], bundle_id))
        return {"message": "Bundle approved"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/coordinator/course/<int:course_id>/bundle/<int:bundle_id>/reject-bundle", methods=['POST'])
@coordinator_auth()
def coordinator_reject_bundle(course_id, bundle_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s LIMIT 1", (bundle_id,))
        if not bundle:
            return {"message": "Bundle not found"}, 404

        if bundle['status'] != BUNDLE_STATUS['waiting-bundles']:
            return {"message": "Bundle is not waiting for approval"}, 400

        db.execute("UPDATE bundle SET status = %s, coordinator_id = %s WHERE id = %s", (BUNDLE_STATUS['rejected-bundles'], coordinator["id"], bundle_id))
        return {"message": "Bundle rejected"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/coordinator/course/<int:course_id>/bundle/<int:bundle_id>/approve-certificate", methods=['POST'])
@coordinator_auth()
def coordinator_approve_certificate(course_id, bundle_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s LIMIT 1", (bundle_id,))
        if not bundle:
            return {"message": "Bundle not found"}, 404

        if bundle['status'] != BUNDLE_STATUS['waiting-approval']:
            return {"message": "Bundle is not waiting for certificate approval"}, 400

        data = request.get_json()
        student_id = data['student_id']

        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE course_id = %s and student_id = %s LIMIT 1", (course_id, student_id))
        if not enrollment:
            return {"message": "Student not enrolled in this course"}, 400

        db.execute("UPDATE enrollment SET is_pass = True, pass_date = NOW() WHERE id = %s", (enrollment['id'],))
        db.execute("UPDATE bundle SET status = %s WHERE id = %s", (BUNDLE_STATUS['accepted-certificates'], bundle_id))
        return {"message": "Certificate approved"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/coordinator/course/<int:course_id>/bundle/<int:bundle_id>/reject-certificate", methods=['POST'])
@coordinator_auth()
def coordinator_reject_certificate(course_id, bundle_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s LIMIT 1", (bundle_id,))
        if not bundle:
            return {"message": "Bundle not found"}, 404

        if bundle['status'] != BUNDLE_STATUS['waiting-approval']:
            return {"message": "Bundle is not waiting for certificate approval"}, 400

        data = request.get_json()
        student_id = data['student_id']

        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE course_id = %s and student_id = %s LIMIT 1", (course_id, student_id))
        if not enrollment:
            return {"message": "Student not enrolled in this course"}, 400

        db.execute("UPDATE enrollment SET is_pass = False, pass_date = NOW() WHERE id = %s", (enrollment['id'],))

        db.execute("UPDATE bundle SET status = %s WHERE id = %s", (BUNDLE_STATUS['rejected-certificates'], bundle_id))
        return {"message": "Certificate rejected"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

#=======================================================================================================
#========================================== ADMIN ======================================================

@app.route("/admin/login", methods=['POST'])
def admin_login():
    try:
        data = request.get_json()
        username = data['username']
        password = data['password']

        if username != app.config['ADMIN_USERNAME'] or password != app.config['ADMIN_PASSWORD']:
            return {"message": "Invalid credentials"}, 401

        token_identity = {
            'type': 'admin',
            'id': 1
        }

        access_token = create_access_token(identity=token_identity)
        return {"access_token": access_token}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/admin/add-coordinator", methods=['POST'])
@admin_auth()
def add_coordinator():
    try:
        data = request.get_json()
        name = data['name']
        surname = data['surname']
        email = data['email']
        password = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE email = %s LIMIT 1", (email,))
        if coordinator:
            return {"message": "Coordinator already exists"}, 400

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        db.execute("INSERT INTO coordinator (name, surname, email, password) VALUES (%s, %s, %s, %s)", (name, surname, email, hashed_password))

        print("Coordinator added successfully. Password: " + password)

        return {"message": f"Coordinator added successfully. Password: {password}"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/admin/coordinators", methods=['GET'])
@admin_auth()
def get_coordinators():
    try:
        coordinators = db.fetch("""
                                SELECT coordinator.id, coordinator.name, coordinator.surname, coordinator.email, department.name as department_name 
                                FROM coordinator 
                                LEFT JOIN department ON coordinator.id = department.coordinator_id
                                """)
        return {"coordinators": coordinators}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/admin/coordinators/<int:coordinator_id>/passive", methods=['POST'])
@admin_auth()
def delete_coordinator(coordinator_id):
    try:
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s LIMIT 1", (coordinator_id,))
        if not coordinator:
            return {"message": "Coordinator not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))
        if department:
            return {"message": "You cannot delete this coordinator"}, 400

        db.execute("UPDATE coordinator SET is_active = False WHERE id = %s", (coordinator_id,))

        return {"message": "Coordinator deleted successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/admin/departments", methods=['GET'])
@admin_auth()
def get_departments():
    try:
        departments = db.fetch("""SELECT department.id, department.name, coordinator.name as coordinator_name, coordinator.surname as coordinator_surname 
                                  FROM department
                                  INNER JOIN coordinator ON department.coordinator_id = coordinator.id
                                  """)
        return {"departments": departments}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/admin/add-department", methods=['POST'])
@admin_auth()
def add_department():
    try:
        data = request.get_json()
        name = data['name']
        coordinator_id = data['coordinator_id']

        department = db.fetch_one("SELECT * FROM department WHERE name = %s LIMIT 1", (name,))
        if department:
            return {"message": "Department already exists"}, 400

        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = False LIMIT 1", (coordinator_id,))
        if not coordinator:
            return {"message": "Coordinator not found"}, 404

        db.execute("UPDATE coordinator SET is_active = True WHERE id = %s", (coordinator_id,))
        db.execute("INSERT INTO department (name, coordinator_id) VALUES (%s, %s)", (name, coordinator_id))

        return {"message": "Department added successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/admin/passive-coordinators", methods=['GET'])
@admin_auth()
def get_passive_coordinators():
    try:
        coordinators = db.fetch("SELECT id, CONCAT(name, ' ', surname) as coordinator_name FROM coordinator WHERE is_active = False")
        return {"coordinators": coordinators}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/admin/departments/<int:department_id>/change-coordinator", methods=['POST'])
@admin_auth()
def change_coordinator(department_id):
    try:
        data = request.get_json()
        coordinator_id = data['coordinator_id']

        department = db.fetch_one("SELECT * FROM department WHERE id = %s LIMIT 1", (department_id,))
        if not department:
            return {"message": "Department not found"}, 404

        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = False LIMIT 1", (coordinator_id,))
        if not coordinator:
            return {"message": "Coordinator not found"}, 404

        if department['coordinator_id']:
            db.execute("UPDATE coordinator SET is_active = False WHERE id = %s", (department['coordinator_id'],))

        db.execute("UPDATE coordinator SET is_active = True WHERE id = %s", (coordinator_id,))
        db.execute("UPDATE department SET coordinator_id = %s WHERE id = %s", (coordinator_id, department_id))
        return {"message": "Coordinator changed successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500





@app.route("/deneme", methods=['GET'])
def create_bundle():
    return "Selamlar"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
