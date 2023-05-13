from flask import Blueprint, request
from flask_jwt_extended import create_access_token, get_jwt
from flask_bcrypt import check_password_hash
from mef_mooc.scripts.util import SEMESTERS, BUNDLE_STATUS
from mef_mooc.scripts.auth import coordinator_auth
from mef_mooc.scripts.models import db

coordinator_app = Blueprint('coordinator_app', __name__, url_prefix='/coordinator')

@coordinator_app.route("/login", methods=['POST'])
def coordinator_login():
    try:
        data = request.get_json()
        email = data['email']
        password = data['password']

        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE email = %s and is_active = True LIMIT 1", (email,))
        if not coordinator:
            return {"message": "Invalid credentials or coordinator disabled"}, 401

        if not check_password_hash(coordinator['password'], password):
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

@coordinator_app.route("/possible-semesters", methods=['GET'])
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

@coordinator_app.route("/add-course", methods=['POST'])
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

@coordinator_app.route("/course/<int:course_id>/passive", methods=['POST'])
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

@coordinator_app.route("/active-courses", methods=['GET'])
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

@coordinator_app.route("/inactive-courses", methods=['GET'])
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

@coordinator_app.route("/course/<int:course_id>/students", methods=['GET'])
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

@coordinator_app.route("/course/<int:course_id>/<status>", methods=['GET'])
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

@coordinator_app.route("/course/<int:course_id>/bundle/<int:bundle_id>/approve-bundle", methods=['POST'])
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

@coordinator_app.route("/course/<int:course_id>/bundle/<int:bundle_id>/reject-bundle", methods=['POST'])
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

@coordinator_app.route("/course/<int:course_id>/bundle/<int:bundle_id>/approve-certificate", methods=['POST'])
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

@coordinator_app.route("/course/<int:course_id>/bundle/<int:bundle_id>/reject-certificate", methods=['POST'])
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
