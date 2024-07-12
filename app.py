import os
from datetime import timedelta
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from functools import wraps
from flask_sqlalchemy import SQLAlchemy 
import datetime
from flask_cors import CORS


app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = '8Zn9Ql0gTvRqW3EzDX4uKX0nPjVqRnGp'
app.config['UPLOAD_FOLDER'] = 'uploads/profile_images'
app.config['PEER_REVIEW_UPLOAD_FOLDER'] = 'uploads/peer_reviews'
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
os.makedirs(app.config['PEER_REVIEW_UPLOAD_FOLDER'], exist_ok=True)
UPLOAD_FOLDER = 'uploads/user_posts'
app.config['USER_POST_UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['USER_POST_UPLOAD_FOLDER'], exist_ok=True)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
jwt = JWTManager(app)




db = SQLAlchemy(app)



#follow
course_followers = db.Table('course_followers',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

# User model
roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)



class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    confirm_password = db.Column(db.String(256), nullable=False)  # Added confirm_password field
    bio = db.Column(db.String(500), nullable=True)
    profile_image = db.Column(db.String(200), nullable=True)

    location = db.relationship('Location', backref='user', uselist=False)
    education = db.relationship('Education', backref='user')
    work_experience = db.relationship('WorkExperience', backref='user')
    licenses_certifications = db.relationship('LicenseCertification', backref='user')
    enrolled_courses = db.relationship('Course', secondary=lambda: enrollment_table, lazy='subquery', backref=db.backref('enrolled_users', lazy='dynamic'))
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    posts = db.relationship('UserPost', backref='user', lazy='dynamic')
    followed_courses = db.relationship('Course', secondary='course_followers', backref='followers')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.email}>'






# Location model
class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    country_region = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)

# Education model
class Education(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    school = db.Column(db.String(100), nullable=True)
    degree = db.Column(db.String(100), nullable=True)
    field_of_study = db.Column(db.String(100), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

# Work Experience model
class WorkExperience(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    company = db.Column(db.String(100), nullable=True)
    role_title = db.Column(db.String(100), nullable=True)
    job_description = db.Column(db.String(500), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

# License and Certification model
class LicenseCertification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100), nullable=True)
    issuing_organization = db.Column(db.String(100), nullable=True)
    issue_date = db.Column(db.Date, nullable=True)
    expiration_date = db.Column(db.Date, nullable=True)
    credentials_id = db.Column(db.String(100), nullable=True)
    credential_url = db.Column(db.String(200), nullable=True)

    #Notification model
    
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
   

    
 


# Course model
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    image = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    video = db.Column(db.String(200), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('courses', lazy='dynamic'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    categories = db.relationship('CourseCategory', backref='course', lazy='dynamic')
    modules = db.relationship('Module', backref='course', lazy='dynamic')

# Module model
class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

# CourseCategory model
class CourseCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

# Enrollment model
enrollment_table = db.Table('enrollment',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
)


 
# Course endpoints
@app.route('/courses', methods=['POST'])
def create_course():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        author_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    data = request.get_json()
    title = data.get('title')
    image = data.get('image')
    content = data.get('content')
    video = data.get('video')
    category_names = data.get('categories', [])
    module_names = data.get('modules', [])

    if not title or not content:
        return jsonify({'error': 'Title and content are required'}), 400

    course = Course(title=title, image=image, content=content, video=video, author_id=author_id)

    for category_name in category_names:
        category = CourseCategory(name=category_name)
        course.categories.append(category)

    for module_name in module_names:
        module = Module(name=module_name)
        course.modules.append(module)

    db.session.add(course)
    db.session.commit()

    return jsonify({'message': 'Course created successfully'}), 201
   

   # Get all courses
@app.route('/courses', methods=['GET'])
def get_courses():
    courses = Course.query.all()
    courses_data = [{'id': course.id, 'title': course.title, 'image': course.image, 'content': course.content,
                     'video': course.video, 'author': course.author.full_name, 'date_created': course.date_created,
                     'categories': [category.name for category in course.categories],
                     'modules': [module.name for module in course.modules]} for course in courses]
    return jsonify(courses_data), 200

# Get a specific course
@app.route('/courses/<int:course_id>', methods=['GET'])
def get_course(course_id):
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    course_data = {'id': course.id, 'title': course.title, 'image': course.image, 'content': course.content,
                   'video': course.video, 'author': course.author.full_name, 'date_created': course.date_created,
                   'categories': [category.name for category in course.categories],
                   'modules': [module.name for module in course.modules]}
    return jsonify(course_data), 200

# Update a course
@app.route('/courses/<int:course_id>', methods=['PUT'])
def update_course(course_id):


# Delete a course
 @app.route('/courses/<int:course_id>', methods=['DELETE'])
 def delete_course(course_id):
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    db.session.delete(course)
    db.session.commit()

    return jsonify({'message': 'Course deleted successfully'}), 200
 
  
  # Create a new category
@app.route('/categories', methods=['POST'])
def create_category():
    data = request.get_json()
    name = data.get('name')

    if not name:
        return jsonify({'error': 'Category name is required'}), 400

    category = CourseCategory(name=name)
    db.session.add(category)
    db.session.commit()

    return jsonify({'message': 'Category created successfully'}), 201

# Get all categories
@app.route('/categories', methods=['GET'])
def get_categories():
    categories = CourseCategory.query.all()
    categories_data = [{'id': category.id, 'name': category.name} for category in categories]
    return jsonify(categories_data), 200

# Update a category
@app.route('/categories/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    category = CourseCategory.query.get(category_id)
    if not category:
        return jsonify({'error': 'Category not found'}), 404

    data = request.get_json()
    name = data.get('name', category.name)

    category.name = name
    db.session.commit()

    return jsonify({'message': 'Category updated successfully'}), 200

# Delete a category
@app.route('/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    category = CourseCategory.query.get(category_id)
    if not category:
        return jsonify({'error': 'Category not found'}), 404

    db.session.delete(category)
    db.session.commit()

    return jsonify({'message': 'Category deleted successfully'}), 200


# Create a new module
@app.route('/modules', methods=['POST'])
def create_module():
    data = request.get_json()
    name = data.get('name')
    course_id = data.get('course_id')

    if not name or not course_id:
        return jsonify({'error': 'Module name and course ID are required'}), 400

    module = Module(name=name, course_id=course_id)
    db.session.add(module)
    db.session.commit()

    return jsonify({'message': 'Module created successfully'}), 201

# Get all modules
@app.route('/modules', methods=['GET'])
def get_modules():
    modules = Module.query.all()
    modules_data = [{'id': module.id, 'name': module.name, 'course_id': module.course_id} for module in modules]
    return jsonify(modules_data), 200

# Update a module
@app.route('/modules/<int:module_id>', methods=['PUT'])
def update_module(module_id):
    module = Module.query.get(module_id)
    if not module:
        return jsonify({'error': 'Module not found'}), 404

    data = request.get_json()
    name = data.get('name', module.name)
    course_id = data.get('course_id', module.course_id)

    module.name = name
    module.course_id = course_id
    db.session.commit()

    return jsonify({'message': 'Module updated successfully'}), 200

# Delete a module
@app.route('/modules/<int:module_id>', methods=['DELETE'])
def delete_module(module_id):
    module = Module.query.get(module_id)
    if not module:
        return jsonify({'error': 'Module not found'}), 404

    db.session.delete(module)
    db.session.commit()

    return jsonify({'message': 'Module deleted successfully'}), 200


    # Enroll in a course
@app.route('/courses/<int:course_id>/enroll', methods=['POST'])
def enroll_in_course(course_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Add the course to the user's enrolled courses (you might need to create a new table or relationship for this)
    user.enrolled_courses.append(course)
    db.session.commit()

    return jsonify({'message': 'Enrolled in the course successfully'}), 200


    # Define upload directory for course videos
COURSE_VIDEO_UPLOAD_FOLDER = 'uploads/course_videos'
app.config['COURSE_VIDEO_UPLOAD_FOLDER'] = COURSE_VIDEO_UPLOAD_FOLDER

# Route to handle course video uploads
@app.route('/upload_course_video/<int:course_id>', methods=['POST'])
def upload_course_video(course_id):
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['COURSE_VIDEO_UPLOAD_FOLDER'], filename))
        course.video = os.path.join(app.config['COURSE_VIDEO_UPLOAD_FOLDER'], filename)
        db.session.commit()
        return jsonify({'message': 'Course video uploaded successfully'}), 200
    else:
        return jsonify({'error': 'Upload failed'}), 500
    


# Register endpoint
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    full_name = data.get('full_name')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    if not full_name or not email or not password or not confirm_password:
        return jsonify({'error': 'All fields are required'}), 400

    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    hashed_confirm_password = generate_password_hash(confirm_password, method='pbkdf2:sha256')

    user = User(full_name=full_name, email=email, password=hashed_password, confirm_password=hashed_confirm_password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201


# Login endpoint
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from datetime import timedelta

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            raise ValueError("No JSON data received")
    except Exception as e:
        app.logger.error(f"Failed to decode JSON object: {e}")
        return jsonify({'message': 'Failed to decode JSON object', 'error': str(e)}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({'message': 'Invalid credentials'}), 401

    # Create access token with longer expiration (e.g., 1 hour)
    access_token = create_access_token(identity=user.email, expires_delta=timedelta(hours=1))
    
    # Create a refresh token
    refresh_token = create_refresh_token(identity=user.email)

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 200

# Add a refresh token route
@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user, expires_delta=timedelta(hours=1))
    return jsonify({'access_token': new_access_token}), 200

# Profile starts here
@app.route('/profile', methods=['GET', 'PUT'])
def profile():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if request.method == 'GET':
        user_data = {
            'full_name': user.full_name,
            'email': user.email,
            'bio': user.bio,
            'profile_image': user.profile_image,
            'location': {
                'country_region': user.location.country_region if user.location else None,
                'city': user.location.city if user.location else None
            },
            'education': [
                {
                    'id': education.id,
                    'school': education.school,
                    'degree': education.degree,
                    'field_of_study': education.field_of_study,
                    'start_date': education.start_date.isoformat() if education.start_date else None,
                    'end_date': education.end_date.isoformat() if education.end_date else None
                } for education in user.education
            ],
            'work_experience': [
                {
                    'id': work.id,
                    'company': work.company,
                    'role_title': work.role_title,
                    'job_description': work.job_description,
                    'start_date': work.start_date.isoformat() if work.start_date else None,
                    'end_date': work.end_date.isoformat() if work.end_date else None
                } for work in user.work_experience
            ],
            'licenses_certifications': [
                {
                    'id': license.id,
                    'name': license.name,
                    'issuing_organization': license.issuing_organization,
                    'issue_date': license.issue_date.isoformat() if license.issue_date else None,
                    'expiration_date': license.expiration_date.isoformat() if license.expiration_date else None,
                    'credentials_id': license.credentials_id,
                    'credential_url': license.credential_url
                } for license in user.licenses_certifications
            ]
        }
        return jsonify(user_data), 200

    if request.method == 'PUT':
        data = request.get_json()

        user.full_name = data.get('full_name', user.full_name)
        user.bio = data.get('bio', user.bio)
        user.profile_image = data.get('profile_image', user.profile_image)

        location_data = data.get('location', {})
        if user.location:
            user.location.country_region = location_data.get('country_region', user.location.country_region)
            user.location.city = location_data.get('city', user.location.city)
        else:
            user.location = Location(
                country_region=location_data.get('country_region'),
                city=location_data.get('city')
            )

        # Update education
        education_data = data.get('education', [])
        for edu_data in education_data:
            education_id = edu_data.get('id')
            if education_id:
                education = Education.query.get(education_id)
                if education:
                    education.school = edu_data.get('school', education.school)
                    education.degree = edu_data.get('degree', education.degree)
                    education.field_of_study = edu_data.get('field_of_study', education.field_of_study)
                    education.start_date = datetime.datetime.fromisoformat(edu_data.get('start_date')) if edu_data.get('start_date') else None
                    education.end_date = datetime.datetime.fromisoformat(edu_data.get('end_date')) if edu_data.get('end_date') else None
            else:
                education = Education(
                    user_id=user.id,
                    school=edu_data.get('school'),
                    degree=edu_data.get('degree'),
                    field_of_study=edu_data.get('field_of_study'),
                    start_date=datetime.datetime.fromisoformat(edu_data.get('start_date')) if edu_data.get('start_date') else None,
                    end_date=datetime.datetime.fromisoformat(edu_data.get('end_date')) if edu_data.get('end_date') else None
                )
                user.education.append(education)

        # Update work experience
        work_experience_data = data.get('work_experience', [])
        for work_data in work_experience_data:
            work_id = work_data.get('id')
            if work_id:
                work = WorkExperience.query.get(work_id)
                if work:
                    work.company = work_data.get('company', work.company)
                    work.role_title = work_data.get('role_title', work.role_title)
                    work.job_description = work_data.get('job_description', work.job_description)
                    work.start_date = datetime.datetime.fromisoformat(work_data.get('start_date')) if work_data.get('start_date') else None
                    work.end_date = datetime.datetime.fromisoformat(work_data.get('end_date')) if work_data.get('end_date') else None
            else:
                work = WorkExperience(
                    user_id=user.id,
                    company=work_data.get('company'),
                    role_title=work_data.get('role_title'),
                    job_description=work_data.get('job_description'),
                    start_date=datetime.datetime.fromisoformat(work_data.get('start_date')) if work_data.get('start_date') else None,
                    end_date=datetime.datetime.fromisoformat(work_data.get('end_date')) if work_data.get('end_date') else None
                )
                user.work_experience.append(work)

        # Update licenses and certifications
        licenses_certifications_data = data.get('licenses_certifications', [])
        for license_data in licenses_certifications_data:
            license_id = license_data.get('id')
            if license_id:
                license = LicenseCertification.query.get(license_id)
                if license:
                    license.name = license_data.get('name', license.name)
                    license.issuing_organization = license_data.get('issuing_organization', license.issuing_organization)
                    license.issue_date = datetime.datetime.fromisoformat(license_data.get('issue_date')) if license_data.get('issue_date') else None
                    license.expiration_date = datetime.datetime.fromisoformat(license_data.get('expiration_date')) if license_data.get('expiration_date') else None
                    license.credentials_id = license_data.get('credentials_id', license.credentials_id)
                    license.credential_url = license_data.get('credential_url', license.credential_url)
            else:
                license = LicenseCertification(
                    user_id=user.id,
                    name=license_data.get('name'),
                    issuing_organization=license_data.get('issuing_organization'),
                    issue_date=datetime.datetime.fromisoformat(license_data.get('issue_date')) if license_data.get('issue_date') else None,
                    expiration_date=datetime.datetime.fromisoformat(license_data.get('expiration_date')) if license_data.get('expiration_date') else None,
                    credentials_id=license_data.get('credentials_id'),
                    credential_url=license_data.get('credential_url')
                )
                user.licenses_certifications.append(license)

        db.session.commit()
        return jsonify({'message': 'Profile updated successfully'}), 200

# Profile code ends here



# Define upload directory# Define upload directory
UPLOAD_FOLDER = 'uploads/profile_images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to get user ID (this is just a placeholder, replace with your actual implementation)
def get_user_id_somehow():
    # For demonstration purposes, let's assume the user ID is submitted in the request form
    user_id = request.form.get('user_id')  
    return user_id

# Route to handle profile image uploads
@app.route('/upload_profile_image', methods=['POST'])
def upload_profile_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        # Save the image path to the database
        user_id = get_user_id_somehow()  # Call the function to get the user ID
        user = User.query.get(user_id)
        user.profile_image = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        db.session.commit()
        return jsonify({'message': 'Profile image uploaded successfully'}), 200
    else:
        return jsonify({'error': 'Upload failed'}), 500
    
     # Image upolad function ends here


  # Blog starts here
  # Blog model
class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    featured_image = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('blogs', lazy='dynamic'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

# Create a new blog post
@app.route('/blogs', methods=['POST'])
def create_blog():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        author_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    data = request.get_json()
    title = data.get('title')
    featured_image = data.get('featured_image')
    content = data.get('content')
    category = data.get('category')

    if not title or not content:
        return jsonify({'error': 'Title and content are required'}), 400

    blog = Blog(title=title, featured_image=featured_image, content=content, category=category, author_id=author_id)

    db.session.add(blog)
    db.session.commit()

    return jsonify({'message': 'Blog post created successfully'}), 201

# Get all blog posts
@app.route('/blogs', methods=['GET'])
def get_blogs():
    blogs = Blog.query.all()
    blogs_data = [{
        'id': blog.id,
        'title': blog.title,
        'featured_image': blog.featured_image,
        'content': blog.content,
        'category': blog.category,
        'author': blog.author.full_name,
        'date_created': blog.date_created
    } for blog in blogs]
    return jsonify(blogs_data), 200

# Get a specific blog post
@app.route('/blogs/<int:blog_id>', methods=['GET'])
def get_blog(blog_id):
    blog = Blog.query.get(blog_id)
    if not blog:
        return jsonify({'error': 'Blog post not found'}), 404

    blog_data = {
        'id': blog.id,
        'title': blog.title,
        'featured_image': blog.featured_image,
        'content': blog.content,
        'category': blog.category,
        'author': blog.author.full_name,
        'date_created': blog.date_created
    }
    return jsonify(blog_data), 200

# Update a blog post
@app.route('/blogs/<int:blog_id>', methods=['PUT'])
def update_blog(blog_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    blog = Blog.query.get(blog_id)
    if not blog:
        return jsonify({'error': 'Blog post not found'}), 404

    if blog.author_id != user_id:
        return jsonify({'error': 'Unauthorized to update this blog post'}), 403

    data = request.get_json()
    blog.title = data.get('title', blog.title)
    blog.featured_image = data.get('featured_image', blog.featured_image)
    blog.content = data.get('content', blog.content)
    blog.category = data.get('category', blog.category)

    db.session.commit()

    return jsonify({'message': 'Blog post updated successfully'}), 200

# Delete a blog post
@app.route('/blogs/<int:blog_id>', methods=['DELETE'])
def delete_blog(blog_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    blog = Blog.query.get(blog_id)
    if not blog:
        return jsonify({'error': 'Blog post not found'}), 404

    if blog.author_id != user_id:
        return jsonify({'error': 'Unauthorized to delete this blog post'}), 403

    db.session.delete(blog)
    db.session.commit()

    return jsonify({'message': 'Blog post deleted successfully'}), 200

    # Blog ends here

    # Message model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')

# Send a message
@app.route('/messages', methods=['POST'])
def send_message():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        sender_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    data = request.get_json()
    recipient_id = data.get('recipient_id')
    content = data.get('content')

    if not recipient_id or not content:
        return jsonify({'error': 'Recipient ID and content are required'}), 400

    recipient = User.query.get(recipient_id)
    if not recipient:
        return jsonify({'error': 'Recipient not found'}), 404

    message = Message(sender_id=sender_id, recipient_id=recipient_id, content=content)
    db.session.add(message)
    db.session.commit()

    return jsonify({'message': 'Message sent successfully'}), 201

# Get messages between two users
@app.route('/messages/<int:other_user_id>', methods=['GET'])
def get_messages(other_user_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    messages = Message.query.filter(
        ((Message.sender_id == user_id) & (Message.recipient_id == other_user_id)) |
        ((Message.sender_id == other_user_id) & (Message.recipient_id == user_id))
    ).order_by(Message.timestamp).all()

    messages_data = [{
        'id': message.id,
        'sender_id': message.sender_id,
        'recipient_id': message.recipient_id,
        'content': message.content,
        'timestamp': message.timestamp,
        'is_read': message.is_read
    } for message in messages]

    return jsonify(messages_data), 200

# Get all messages for a user
@app.route('/messages', methods=['GET'])
def get_all_messages():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    sent_messages = Message.query.filter_by(sender_id=user_id).all()
    received_messages = Message.query.filter_by(recipient_id=user_id).all()

    messages_data = []
    for message in sent_messages + received_messages:
        other_user = message.recipient if message.sender_id == user_id else message.sender
        messages_data.append({
            'id': message.id,
            'other_user_id': other_user.id,
            'other_user_name': other_user.full_name,
            'content': message.content,
            'timestamp': message.timestamp,
            'is_read': message.is_read,
            'is_sent': message.sender_id == user_id
        })

    # Sort messages by timestamp
    messages_data.sort(key=lambda x: x['timestamp'], reverse=True)

    return jsonify(messages_data), 200

# Mark a message as read
@app.route('/messages/<int:message_id>/read', methods=['PUT'])
def mark_message_as_read(message_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    message = Message.query.get(message_id)
    if not message:
        return jsonify({'error': 'Message not found'}), 404

    if message.recipient_id != user_id:
        return jsonify({'error': 'Unauthorized to mark this message as read'}), 403

    message.is_read = True
    db.session.commit()

    return jsonify({'message': 'Message marked as read'}), 200

# Delete a message

#peer review


# PeerReview model
class PeerReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    submitter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    document_path = db.Column(db.String(255), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    submission_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    review_date = db.Column(db.DateTime, nullable=True)

    course = db.relationship('Course', backref='peer_reviews')
    submitter = db.relationship('User', foreign_keys=[submitter_id], backref='submitted_reviews')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id], backref='reviewed_reviews')

# Upload a document for peer review
@app.route('/peer-review/upload', methods=['POST'])
def upload_peer_review():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        submitter_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    course_id = request.form.get('course_id')

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and course_id:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['PEER_REVIEW_UPLOAD_FOLDER'], filename)
        file.save(file_path)

        peer_review = PeerReview(
            course_id=course_id,
            submitter_id=submitter_id,
            document_path=file_path
        )
        db.session.add(peer_review)
        db.session.commit()

        return jsonify({'message': 'Document uploaded successfully for peer review'}), 201
    else:
        return jsonify({'error': 'Invalid request'}), 400

# Get documents available for review in a course
@app.route('/peer-review/available/<int:course_id>', methods=['GET'])
def get_available_reviews(course_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    available_reviews = PeerReview.query.filter_by(
        course_id=course_id,
        reviewer_id=None
    ).filter(PeerReview.submitter_id != user_id).all()

    reviews_data = [{
        'id': review.id,
        'submitter_name': review.submitter.full_name,
        'submission_date': review.submission_date,
        'document_path': review.document_path
    } for review in available_reviews]

    return jsonify(reviews_data), 200

# Download a document for review
@app.route('/peer-review/download/<int:review_id>', methods=['GET'])
def download_review_document(review_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
    except:
        return jsonify({'error': 'Invalid token'}), 401

    review = PeerReview.query.get(review_id)
    if not review:
        return jsonify({'error': 'Review not found'}), 404

    return send_file(review.document_path, as_attachment=True)

# Submit a review
@app.route('/peer-review/submit/<int:review_id>', methods=['POST'])
def submit_review(review_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        reviewer_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    review = PeerReview.query.get(review_id)
    if not review:
        return jsonify({'error': 'Review not found'}), 404

    if review.reviewer_id is not None:
        return jsonify({'error': 'This document has already been reviewed'}), 400

    data = request.get_json()
    remarks = data.get('remarks')

    if not remarks:
        return jsonify({'error': 'Remarks are required'}), 400

    review.reviewer_id = reviewer_id
    review.remarks = remarks
    review.review_date = datetime.datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Review submitted successfully'}), 200

# Get reviews for a user's submitted documents
@app.route('/peer-review/my-submissions', methods=['GET'])
def get_my_submissions():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    submissions = PeerReview.query.filter_by(submitter_id=user_id).all()

    submissions_data = [{
        'id': submission.id,
        'course_name': submission.course.title,
        'submission_date': submission.submission_date,
        'reviewer_name': submission.reviewer.full_name if submission.reviewer else None,
        'review_date': submission.review_date,
        'remarks': submission.remarks
    } for submission in submissions]

    return jsonify(submissions_data), 200

    #Admin

    # Admin model
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Role model
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

# Instructor model
class Instructor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    course = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Create initial admin
@app.route('/create-admin', methods=['POST'])
def create_admin():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    if Admin.query.filter_by(username=username).first():
        return jsonify({'error': 'Admin already exists'}), 400

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    admin = Admin(username=username, password=hashed_password)
    db.session.add(admin)
    db.session.commit()

    return jsonify({'message': 'Admin created successfully'}), 201

# Admin login
@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    admin = Admin.query.filter_by(username=username).first()

    if not admin or admin.password != password:
        return jsonify({'error': 'Invalid credentials'}), 401

    token = jwt.encode({
        'admin_id': admin.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'])

    return jsonify({'token': token}), 200

# Admin middleware
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Admin token is missing'}), 401

        try:
            data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
            admin_id = data['admin_id']
            admin = Admin.query.get(admin_id)
            if not admin:
                raise ValueError('Admin not found')
        except:
            return jsonify({'error': 'Invalid admin token'}), 401

        return f(*args, **kwargs)

    return decorated

# Create role
@app.route('/admin/roles', methods=['POST'])
@admin_required
def create_role():
    data = request.get_json()
    name = data.get('name')

    if not name:
        return jsonify({'error': 'Role name is required'}), 400

    if Role.query.filter_by(name=name).first():
        return jsonify({'error': 'Role already exists'}), 400

    role = Role(name=name)
    db.session.add(role)
    db.session.commit()

    return jsonify({'message': 'Role created successfully'}), 201

# Delete role
@app.route('/admin/roles/<int:role_id>', methods=['DELETE'])
@admin_required
def delete_role(role_id):
    role = Role.query.get(role_id)
    if not role:
        return jsonify({'error': 'Role not found'}), 404

    db.session.delete(role)
    db.session.commit()

    return jsonify({'message': 'Role deleted successfully'}), 200

# Create instructor
@app.route('/admin/instructors', methods=['POST'])
@admin_required
def create_instructor():
    data = request.get_json()
    full_name = data.get('full_name')
    email = data.get('email')
    course = data.get('course')
    phone = data.get('phone')
    password = data.get('password')

    if not full_name or not email or not course or not phone or not password:
        return jsonify({'error': 'All fields are required'}), 400

    if Instructor.query.filter_by(email=email).first():
        return jsonify({'error': 'Instructor with this email already exists'}), 400

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    instructor = Instructor(full_name=full_name, email=email, course=course, phone=phone, password=hashed_password)
    db.session.add(instructor)
    db.session.commit()

    return jsonify({'message': 'Instructor created successfully'}), 201

# Get all instructors
@app.route('/admin/instructors', methods=['GET'])
@admin_required
def get_instructors():
    instructors = Instructor.query.all()
    instructors_data = [{
        'id': instructor.id,
        'full_name': instructor.full_name,
        'email': instructor.email,
        'course': instructor.course,
        'phone': instructor.phone
    } for instructor in instructors]

    return jsonify(instructors_data), 200

# Delete instructor
@app.route('/admin/instructors/<int:instructor_id>', methods=['DELETE'])
@admin_required
def delete_instructor(instructor_id):
    instructor = Instructor.query.get(instructor_id)
    if not instructor:
        return jsonify({'error': 'Instructor not found'}), 404

    db.session.delete(instructor)
    db.session.commit()

    return jsonify({'message': 'Instructor deleted successfully'}), 200

# Instructor login
@app.route('/instructor/login', methods=['POST'])
def instructor_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    instructor = Instructor.query.filter_by(email=email).first()

    if not instructor or instructor.password != password:
        return jsonify({'error': 'Invalid credentials'}), 401

    token = jwt.encode({
        'instructor_id': instructor.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'])

    return jsonify({'token': token}), 200

    # Assign role to user
@app.route('/admin/assign-role', methods=['POST'])
@admin_required
def assign_role():
    data = request.get_json()
    user_id = data.get('user_id')
    role_id = data.get('role_id')

    if not user_id or not role_id:
        return jsonify({'error': 'User ID and Role ID are required'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    role = Role.query.get(role_id)
    if not role:
        return jsonify({'error': 'Role not found'}), 404

    if role in user.roles:
        return jsonify({'message': 'User already has this role'}), 200

    user.roles.append(role)
    db.session.commit()

    return jsonify({'message': 'Role assigned successfully'}), 200

# Remove role from user
@app.route('/admin/remove-role', methods=['POST'])
@admin_required
def remove_role():
    data = request.get_json()
    user_id = data.get('user_id')
    role_id = data.get('role_id')

    if not user_id or not role_id:
        return jsonify({'error': 'User ID and Role ID are required'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    role = Role.query.get(role_id)
    if not role:
        return jsonify({'error': 'Role not found'}), 404

    if role not in user.roles:
        return jsonify({'message': 'User does not have this role'}), 200

    user.roles.remove(role)
    db.session.commit()

    return jsonify({'message': 'Role removed successfully'}), 200

# Get user roles
@app.route('/admin/user-roles/<int:user_id>', methods=['GET'])
@admin_required
def get_user_roles(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    roles = [{'id': role.id, 'name': role.name} for role in user.roles]
    return jsonify(roles), 200

# Get all users with their roles
@app.route('/admin/users-with-roles', methods=['GET'])
@admin_required
def get_users_with_roles():
    users = User.query.all()
    users_data = [{
        'id': user.id,
        'full_name': user.full_name,
        'email': user.email,
        'roles': [{'id': role.id, 'name': role.name} for role in user.roles]
    } for user in users]

    return jsonify(users_data), 200

    #user post
class UserPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    executive_summary = db.Column(db.Text, nullable=False)
    document_path = db.Column(db.String(255), nullable=True)
    subject = db.Column(db.String(100), nullable=False)
    doi_link = db.Column(db.String(255), nullable=True)
    video_link = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    # The relationship is now defined in the User model, so we don't need to repeat it here

  

# Make sure to create a directory for storing uploaded documents


@app.route('/user/posts', methods=['POST'])
def create_user_post():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    title = request.form.get('title')
    executive_summary = request.form.get('executive_summary')
    subject = request.form.get('subject')
    doi_link = request.form.get('doi_link')
    video_link = request.form.get('video_link')

    if not title or not executive_summary or not subject:
        return jsonify({'error': 'Title, executive summary, and subject are required'}), 400

    # Check if the subject matches a course title
    if not Course.query.filter_by(title=subject).first():
        return jsonify({'error': 'Invalid subject. Must match a course title.'}), 400

    document_path = None
    if 'document' in request.files:
        file = request.files['document']
        if file.filename != '':
            filename = secure_filename(file.filename)
            document_path = os.path.join(app.config['USER_POST_UPLOAD_FOLDER'], filename)
            file.save(document_path)

    post = UserPost(
        user_id=user_id,
        title=title,
        executive_summary=executive_summary,
        document_path=document_path,
        subject=subject,
        doi_link=doi_link,
        video_link=video_link
    )

    db.session.add(post)
    db.session.commit()

    return jsonify({'message': 'Post created successfully', 'post_id': post.id}), 201

@app.route('/user/posts', methods=['GET'])
def get_user_posts():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    posts = UserPost.query.filter_by(user_id=user_id).order_by(UserPost.created_at.desc()).all()

    posts_data = [{
        'id': post.id,
        'title': post.title,
        'executive_summary': post.executive_summary,
        'document_path': post.document_path,
        'subject': post.subject,
        'doi_link': post.doi_link,
        'video_link': post.video_link,
        'created_at': post.created_at
    } for post in posts]

    return jsonify(posts_data), 200

@app.route('/user/posts/<int:post_id>', methods=['GET'])
def get_user_post(post_id):
    post = UserPost.query.get(post_id)
    if not post:
        return jsonify({'error': 'Post not found'}), 404

    post_data = {
        'id': post.id,
        'title': post.title,
        'executive_summary': post.executive_summary,
        'document_path': post.document_path,
        'subject': post.subject,
        'doi_link': post.doi_link,
        'video_link': post.video_link,
        'created_at': post.created_at,
        'user': {
            'id': post.user.id,
            'full_name': post.user.full_name
        }
    }

    return jsonify(post_data), 200


#follow
# This is the original get_courses function


# This is the renamed function for the follow feature
@app.route('/courses_for_follow', methods=['GET'])
def get_courses_for_follow():
    courses = Course.query.all()
    return jsonify([{'id': c.id, 'title': c.title} for c in courses]), 200

@app.route('/follow_course/<int:course_id>', methods=['POST'])
def follow_course(course_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    user = User.query.get(user_id)
    course = Course.query.get(course_id)

    if not course:
        return jsonify({'error': 'Course not found'}), 404

    if course in user.followed_courses:
        return jsonify({'message': 'Already following this course'}), 200

    user.followed_courses.append(course)
    db.session.commit()

    return jsonify({'message': 'Course followed successfully'}), 200

@app.route('/unfollow_course/<int:course_id>', methods=['POST'])
def unfollow_course(course_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    user = User.query.get(user_id)
    course = Course.query.get(course_id)

    if not course:
        return jsonify({'error': 'Course not found'}), 404

    if course not in user.followed_courses:
        return jsonify({'message': 'Not following this course'}), 200

    user.followed_courses.remove(course)
    db.session.commit()

    return jsonify({'message': 'Course unfollowed successfully'}), 200

@app.route('/user/followed_posts', methods=['GET'])
def get_followed_posts():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    user = User.query.get(user_id)
    followed_courses = user.followed_courses

    posts = UserPost.query.filter(UserPost.subject.in_([c.title for c in followed_courses])).order_by(UserPost.created_at.desc()).all()

    posts_data = [{
        'id': post.id,
        'title': post.title,
        'executive_summary': post.executive_summary,
        'subject': post.subject,
        'doi_link': post.doi_link,
        'video_link': post.video_link,
        'created_at': post.created_at,
        'user': {
            'id': post.user.id,
            'full_name': post.user.full_name
        }
    } for post in posts]

    return jsonify(posts_data), 200


    #Notification
    # Create a notification
@app.route('/notifications', methods=['POST'])
def create_notification():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    content = request.json.get('content')
    if not content:
        return jsonify({'error': 'Notification content is required'}), 400

    notification = Notification(user_id=user_id, content=content)
    db.session.add(notification)
    db.session.commit()

    return jsonify({'message': 'Notification created successfully', 'id': notification.id}), 201

# Get all notifications for a user
@app.route('/notifications', methods=['GET'])
def get_notifications():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).all()
    notifications_data = [{
        'id': notif.id,
        'content': notif.content,
        'is_read': notif.is_read,
        'created_at': notif.created_at
    } for notif in notifications]

    return jsonify(notifications_data), 200

# Mark a notification as read
@app.route('/notifications/<int:notification_id>/read', methods=['PUT'])
def mark_notification_as_read(notification_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404

    notification.is_read = True
    db.session.commit()

    return jsonify({'message': 'Notification marked as read'}), 200

# Delete a notification
@app.route('/notifications/<int:notification_id>', methods=['DELETE'])
def delete_notification(notification_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401

    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404

    db.session.delete(notification)
    db.session.commit()

    return jsonify({'message': 'Notification deleted successfully'}), 200






if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

