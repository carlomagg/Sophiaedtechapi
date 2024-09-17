import os
from datetime import timedelta
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from functools import wraps
from flask_sqlalchemy import SQLAlchemy 
import datetime
from dateutil import parser
from flask_cors import CORS
from PIL import Image
import io
import cloudinary
import cloudinary.uploader
from sqlalchemy import or_
import openai

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024
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
PROFILE_IMAGE_UPLOAD_FOLDER = 'uploads/profile_images'
app.config['PROFILE_IMAGE_UPLOAD_FOLDER'] = PROFILE_IMAGE_UPLOAD_FOLDER
jwt = JWTManager(app)

openai.api_key = "your-openai-api-key"


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

admin_roles = db.Table('admin_roles',
    db.Column('admin_id', db.Integer, db.ForeignKey('admin.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    confirm_password = db.Column(db.String(256), nullable=False)
    bio = db.Column(db.String(500), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)  # New field
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


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


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
#class Course(db.Model):
   # id = db.Column(db.Integer, primary_key=True)
   # title = db.Column(db.String(200), nullable=False)
   ## image = db.Column(db.String(200), nullable=True)
    #content = db.Column(db.Text, nullable=False)
    #video = db.Column(db.String(200), nullable=True)
    ##brief = db.Column(db.Text, nullable=True)
   # number_of_modules = db.Column(db.Integer, default=0)
    ##author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
   # author = db.relationship('User', backref=db.backref('courses', lazy='dynamic'))
   # date_created = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
   # categories = db.relationship('CourseCategory', backref='course', lazy='dynamic')
   # modules = db.relationship('Module', backref='course', lazy='dynamic')
   # categories = db.relationship('CourseCategory', secondary='course_category_association', back_populates='courses')

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    image = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    video = db.Column(db.String(200), nullable=True)
    brief = db.Column(db.Text, nullable=True)
    number_of_modules = db.Column(db.Integer, default=0)
    course_type = db.Column(db.String(50), nullable=True)  # New field
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('courses', lazy='dynamic'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    categories = db.relationship('CourseCategory', secondary='course_category_association', back_populates='courses')
    modules = db.relationship('Module', backref='course', lazy='dynamic')

# Module model
class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

# CourseCategory model
class CourseCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    courses = db.relationship('Course', secondary='course_category_association', back_populates='categories')

# Create an association table
course_category_association = db.Table('course_category_association',
    db.Column('course_id', db.Integer, db.ForeignKey('course.id')),
    db.Column('category_id', db.Integer, db.ForeignKey('course_category.id'))
)

# Enrollment model
enrollment_table = db.Table('enrollment',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
)


 
# Course endpoints
@app.route('/courses', methods=['POST'])
@jwt_required()
def create_course():
    author_id = get_jwt_identity()
    
    data = request.get_json()
    title = data.get('title')
    image = data.get('image')
    content = data.get('content')
    video = data.get('video')
    brief = data.get('brief')
    number_of_modules = data.get('number_of_modules', 0)
    course_type = data.get('course_type')  # New field
    category_names = data.get('categories', [])
    module_names = data.get('modules', [])

    if not title or not content:
        return jsonify({'error': 'Title and content are required'}), 400

    course = Course(
        title=title, 
        image=image, 
        content=content, 
        video=video, 
        brief=brief, 
        number_of_modules=number_of_modules,
        course_type=course_type,  # New field
        author_id=author_id
    )

    for category_name in category_names:
        category = CourseCategory.query.filter_by(name=category_name).first()
        if not category:
            category = CourseCategory(name=category_name)
            db.session.add(category)
        course.categories.append(category)

    for module_name in module_names:
        module = Module(name=module_name, course=course)
        db.session.add(module)

    db.session.add(course)
    db.session.commit()

    return jsonify({'message': 'Course created successfully'}), 201
   

   # Get all courses
@app.route('/courses', methods=['GET'])
def get_courses():
    courses = Course.query.all()
    courses_data = []
    for course in courses:
        course_dict = {
            'id': course.id,
            'title': course.title,
            'image': course.image,
            'content': course.content,
            'video': course.video,
            'brief': course.brief,
            'number_of_modules': course.number_of_modules,
            'course_type': course.course_type,  # New field
            'date_created': course.date_created.isoformat() if course.date_created else None,
            'categories': [category.name for category in course.categories],
            'modules': [module.name for module in course.modules]
        }
        
        # Handle case where author might be None
        if course.author:
            course_dict['author'] = course.author.full_name
        else:
            course_dict['author'] = 'Unknown'

        courses_data.append(course_dict)

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
@jwt_required()
def update_course(course_id):
    user_id = get_jwt_identity()
    
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    # Check if the current user is the author of the course
    if course.author_id != user_id:
        return jsonify({'error': 'Unauthorized to update this course'}), 403

    data = request.get_json()

    # Update basic course information
    course.title = data.get('title', course.title)
    course.image = data.get('image', course.image)
    course.content = data.get('content', course.content)
    course.video = data.get('video', course.video)

    # Update categories
    if 'categories' in data:
        # Remove all existing categories
        course.categories = []
        # Add new categories
        for category_name in data['categories']:
            category = CourseCategory.query.filter_by(name=category_name).first()
            if not category:
                category = CourseCategory(name=category_name)
            course.categories.append(category)

    # Update modules
    if 'modules' in data:
        # Remove all existing modules
        for module in course.modules:
            db.session.delete(module)
        course.modules = []
        # Add new modules
        for module_data in data['modules']:
            module = Module(
                name=module_data.get('name'),
                content=module_data.get('content'),
                order=module_data.get('order')
            )
            course.modules.append(module)

    try:
        db.session.commit()
        return jsonify({'message': 'Course updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update course: {str(e)}'}), 500


# Delete a course
    @app.route('/courses/<int:course_id>', methods=['DELETE'])
    @jwt_required()
    def delete_course(course_id):
     user_id = get_jwt_identity()
    
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    # Check if the current user is the author of the course
    if course.author_id != user_id:
        return jsonify({'error': 'Unauthorized to delete this course'}), 403

    try:
        # Remove all enrollments for this course
        for enrollment in course.enrollments:
            db.session.delete(enrollment)
        
        # Remove all modules associated with this course
        for module in course.modules:
            db.session.delete(module)
        
        # Remove all category associations
        course.categories = []
        
        # Delete the course
        db.session.delete(course)
        db.session.commit()
        
        return jsonify({'message': 'Course deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete course: {str(e)}'}), 500
 
  
  # Create a new category
@app.route('/categories', methods=['POST'])
def create_category():
    data = request.get_json()
    name = data.get('name')

    if not name:
        return jsonify({'error': 'Category name is required'}), 400

    existing_category = CourseCategory.query.filter_by(name=name).first()
    if existing_category:
        return jsonify({'error': 'Category already exists'}), 400

    category = CourseCategory(name=name)
    db.session.add(category)
    db.session.commit()

    return jsonify({'message': 'Category created successfully', 'id': category.id}), 201

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
@jwt_required()
def create_module():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    course_id = data.get('course_id')

    if not name or not course_id:
        return jsonify({'error': 'Module name and course ID are required'}), 400

    module = Module(name=name, description=description, course_id=course_id)
    db.session.add(module)
    
    course = Course.query.get(course_id)
    if course:
        course.number_of_modules += 1
    
    db.session.commit()

    return jsonify({'message': 'Module created successfully'}), 201


# Get all modules
@app.route('/modules', methods=['GET'])
def get_modules():
    modules = Module.query.all()
    modules_data = [{'id': module.id, 'name': module.name, 'description': module.description, 'course_id': module.course_id} for module in modules]
    return jsonify(modules_data), 200

# Update a module
@app.route('/modules/<int:module_id>', methods=['PUT'])
@jwt_required()
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
@jwt_required()
def delete_module(module_id):
    module = Module.query.get(module_id)
    if not module:
        return jsonify({'error': 'Module not found'}), 404

    db.session.delete(module)
    db.session.commit()

    return jsonify({'message': 'Module deleted successfully'}), 200


    # Enroll in a course
@app.route('/courses/<int:course_id>/enroll', methods=['POST'])
@jwt_required()
def enroll_in_course(course_id):
    user_id = get_jwt_identity()

    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Add the course to the user's enrolled courses
    user.enrolled_courses.append(course)
    db.session.commit()

    return jsonify({'message': 'Enrolled in the course successfully'}), 200


    # Define upload directory for course videos
COURSE_VIDEO_UPLOAD_FOLDER = 'uploads/course_videos'
app.config['COURSE_VIDEO_UPLOAD_FOLDER'] = COURSE_VIDEO_UPLOAD_FOLDER

# Route to handle course video uploads
@app.route('/upload_course_video/<int:course_id>', methods=['POST'])
@jwt_required()
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
@jwt_required()
def profile():
    user_email = get_jwt_identity()
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if request.method == 'GET':
        user_data = {
            'id': user.id,
            'full_name': user.full_name,
            'email': user.email,
            'bio': user.bio,
            'phone_number': user.phone_number,  # Add this line
            'profile_image': user.profile_image,
            'location': {
                'country_region': user.location.country_region if user.location else None,
                'city': user.location.city if user.location else None
            },
            'education': [{
                'id': edu.id,
                'school': edu.school,
                'degree': edu.degree,
                'field_of_study': edu.field_of_study,
                'start_date': edu.start_date.isoformat() if edu.start_date else None,
                'end_date': edu.end_date.isoformat() if edu.end_date else None
            } for edu in user.education],
            'work_experience': [{
                'id': work.id,
                'company': work.company,
                'role_title': work.role_title,
                'job_description': work.job_description,
                'start_date': work.start_date.isoformat() if work.start_date else None,
                'end_date': work.end_date.isoformat() if work.end_date else None
            } for work in user.work_experience],
            'licenses_certifications': [{
                'id': lic.id,
                'name': lic.name,
                'issuing_organization': lic.issuing_organization,
                'issue_date': lic.issue_date.isoformat() if lic.issue_date else None,
                'expiration_date': lic.expiration_date.isoformat() if lic.expiration_date else None,
                'credentials_id': lic.credentials_id,
                'credential_url': lic.credential_url
            } for lic in user.licenses_certifications]
        }
        return jsonify(user_data), 200

    if request.method == 'PUT':
        data = request.get_json()

        # Check if the new email already exists
        new_email = data.get('email')
        if new_email and new_email != user.email:
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user:
                return jsonify({'error': 'Email already in use'}), 400

        user.full_name = data.get('full_name', user.full_name)
        user.email = new_email or user.email
        user.bio = data.get('bio', user.bio)
        user.phone_number = data.get('phone_number', user.phone_number)  # Add this line
        user.profile_image = data.get('profile_image', user.profile_image)

        # Update location
        location_data = data.get('location', {})
        if user.location:
            user.location.country_region = location_data.get('country_region', user.location.country_region)
            user.location.city = location_data.get('city', user.location.city)
        else:
            user.location = Location(
                user_id=user.id,
                country_region=location_data.get('country_region'),
                city=location_data.get('city')
            )

        # Update education
        education_data = data.get('education', [])
        for edu_data in education_data:
            education_id = edu_data.get('id')
            education = Education.query.get(education_id) if education_id else None
            if education:
                education.school = edu_data.get('school', education.school)
                education.degree = edu_data.get('degree', education.degree)
                education.field_of_study = edu_data.get('field_of_study', education.field_of_study)
                education.start_date = parser.parse(edu_data.get('start_date')) if edu_data.get('start_date') else None
                education.end_date = parser.parse(edu_data.get('end_date')) if edu_data.get('end_date') else None
            else:
                education = Education(
                    user_id=user.id,
                    school=edu_data.get('school'),
                    degree=edu_data.get('degree'),
                    field_of_study=edu_data.get('field_of_study'),
                    start_date=parser.parse(edu_data.get('start_date')) if edu_data.get('start_date') else None,
                    end_date=parser.parse(edu_data.get('end_date')) if edu_data.get('end_date') else None
                )
                db.session.add(education)

        # Update work experience
        work_experience_data = data.get('work_experience', [])
        for work_data in work_experience_data:
            work_id = work_data.get('id')
            work = WorkExperience.query.get(work_id) if work_id else None
            if work:
                work.company = work_data.get('company', work.company)
                work.role_title = work_data.get('role_title', work.role_title)
                work.job_description = work_data.get('job_description', work.job_description)
                work.start_date = parser.parse(work_data.get('start_date')) if work_data.get('start_date') else None
                work.end_date = parser.parse(work_data.get('end_date')) if work_data.get('end_date') else None
            else:
                work = WorkExperience(
                    user_id=user.id,
                    company=work_data.get('company'),
                    role_title=work_data.get('role_title'),
                    job_description=work_data.get('job_description'),
                    start_date=parser.parse(work_data.get('start_date')) if work_data.get('start_date') else None,
                    end_date=parser.parse(work_data.get('end_date')) if work_data.get('end_date') else None
                )
                db.session.add(work)

        # Update licenses and certifications
        licenses_certifications_data = data.get('licenses_certifications', [])
        for license_data in licenses_certifications_data:
            license_id = license_data.get('id')
            license = LicenseCertification.query.get(license_id) if license_id else None
            if license:
                license.name = license_data.get('name', license.name)
                license.issuing_organization = license_data.get('issuing_organization', license.issuing_organization)
                license.issue_date = parser.parse(license_data.get('issue_date')) if license_data.get('issue_date') else None
                license.expiration_date = parser.parse(license_data.get('expiration_date')) if license_data.get('expiration_date') else None
                license.credentials_id = license_data.get('credentials_id', license.credentials_id)
                license.credential_url = license_data.get('credential_url', license.credential_url)
            else:
                license = LicenseCertification(
                    user_id=user.id,
                    name=license_data.get('name'),
                    issuing_organization=license_data.get('issuing_organization'),
                    issue_date=parser.parse(license_data.get('issue_date')) if license_data.get('issue_date') else None,
                    expiration_date=parser.parse(license_data.get('expiration_date')) if license_data.get('expiration_date') else None,
                    credentials_id=license_data.get('credentials_id'),
                    credential_url=license_data.get('credential_url')
                )
                db.session.add(license)

        try:
            db.session.commit()
            return jsonify({'message': 'Profile updated successfully'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'An error occurred: {str(e)}'}), 500

    # This should never be reached, but add it as a safeguard
    return jsonify({'error': 'Invalid request method'}), 405


#add/delete profile items
@app.route('/user/experience', methods=['POST', 'DELETE'])
@jwt_required()
def manage_experience():
    user_email = get_jwt_identity()
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if request.method == 'POST':
        data = request.get_json()
        new_experience = WorkExperience(
            user_id=user.id,
            company=data.get('company'),
            role_title=data.get('role_title'),
            job_description=data.get('job_description'),
            start_date=parser.parse(data.get('start_date')) if data.get('start_date') else None,
            end_date=parser.parse(data.get('end_date')) if data.get('end_date') else None
        )
        db.session.add(new_experience)

        try:
            db.session.commit()
            return jsonify({'message': 'Experience added successfully', 'id': new_experience.id}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'An error occurred: {str(e)}'}), 500

    elif request.method == 'DELETE':
        experience_id = request.args.get('id')
        if not experience_id:
            return jsonify({'error': 'Experience ID is required'}), 400

        experience = WorkExperience.query.get(experience_id)
        if not experience or experience.user_id != user.id:
            return jsonify({'error': 'Experience not found or not authorized'}), 404

        db.session.delete(experience)

        try:
            db.session.commit()
            return jsonify({'message': 'Experience deleted successfully'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'An error occurred: {str(e)}'}), 500

    return jsonify({'error': 'Invalid request method'}), 405

@app.route('/user/education', methods=['POST', 'DELETE'])
@jwt_required()
def manage_education():
    user_email = get_jwt_identity()
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if request.method == 'POST':
        data = request.get_json()
        new_education = Education(
            user_id=user.id,
            school=data.get('school'),
            degree=data.get('degree'),
            field_of_study=data.get('field_of_study'),
            start_date=parser.parse(data.get('start_date')) if data.get('start_date') else None,
            end_date=parser.parse(data.get('end_date')) if data.get('end_date') else None
        )
        db.session.add(new_education)

        try:
            db.session.commit()
            return jsonify({'message': 'Education added successfully', 'id': new_education.id}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'An error occurred: {str(e)}'}), 500

    elif request.method == 'DELETE':
        education_id = request.args.get('id')
        if not education_id:
            return jsonify({'error': 'Education ID is required'}), 400

        education = Education.query.get(education_id)
        if not education or education.user_id != user.id:
            return jsonify({'error': 'Education not found or not authorized'}), 404

        db.session.delete(education)

        try:
            db.session.commit()
            return jsonify({'message': 'Education deleted successfully'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'An error occurred: {str(e)}'}), 500

    return jsonify({'error': 'Invalid request method'}), 405

@app.route('/user/license', methods=['POST', 'DELETE'])
@jwt_required()
def manage_license():
    user_email = get_jwt_identity()
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if request.method == 'POST':
        data = request.get_json()
        new_license = LicenseCertification(
            user_id=user.id,
            name=data.get('name'),
            issuing_organization=data.get('issuing_organization'),
            issue_date=parser.parse(data.get('issue_date')) if data.get('issue_date') else None,
            expiration_date=parser.parse(data.get('expiration_date')) if data.get('expiration_date') else None,
            credentials_id=data.get('credentials_id'),
            credential_url=data.get('credential_url')
        )
        db.session.add(new_license)

        try:
            db.session.commit()
            return jsonify({'message': 'License/Certification added successfully', 'id': new_license.id}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'An error occurred: {str(e)}'}), 500

    elif request.method == 'DELETE':
        license_id = request.args.get('id')
        if not license_id:
            return jsonify({'error': 'License/Certification ID is required'}), 400

        license = LicenseCertification.query.get(license_id)
        if not license or license.user_id != user.id:
            return jsonify({'error': 'License/Certification not found or not authorized'}), 404

        db.session.delete(license)

        try:
            db.session.commit()
            return jsonify({'message': 'License/Certification deleted successfully'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'An error occurred: {str(e)}'}), 500

    return jsonify({'error': 'Invalid request method'}), 405


    #user endpoint

@app.route('/users', methods=['GET'])
@jwt_required()
def get_all_users():
    users = User.query.all()
    users_data = [
        {
            'id': user.id,
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
        } for user in users
    ]
    return jsonify(users_data), 200

@app.route('/user/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted successfully'}), 200


    @app.route('/user/<int:user_id>', methods=['PUT'])
    @jwt_required()
    def update_user(user_id):
     user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    user.full_name = data.get('full_name', user.full_name)
    user.email = data.get('email', user.email)
    user.bio = data.get('bio', user.bio)
    user.profile_image = data.get('profile_image', user.profile_image)

    # Update location
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
            if education and education.user_id == user.id:
                education.school = edu_data.get('school', education.school)
                education.degree = edu_data.get('degree', education.degree)
                education.field_of_study = edu_data.get('field_of_study', education.field_of_study)
                education.start_date = datetime.fromisoformat(edu_data.get('start_date')) if edu_data.get('start_date') else None
                education.end_date = datetime.fromisoformat(edu_data.get('end_date')) if edu_data.get('end_date') else None
        else:
            education = Education(
                user_id=user.id,
                school=edu_data.get('school'),
                degree=edu_data.get('degree'),
                field_of_study=edu_data.get('field_of_study'),
                start_date=datetime.fromisoformat(edu_data.get('start_date')) if edu_data.get('start_date') else None,
                end_date=datetime.fromisoformat(edu_data.get('end_date')) if edu_data.get('end_date') else None
            )
            user.education.append(education)

    # Update work experience
    work_experience_data = data.get('work_experience', [])
    for work_data in work_experience_data:
        work_id = work_data.get('id')
        if work_id:
            work = WorkExperience.query.get(work_id)
            if work and work.user_id == user.id:
                work.company = work_data.get('company', work.company)
                work.role_title = work_data.get('role_title', work.role_title)
                work.job_description = work_data.get('job_description', work.job_description)
                work.start_date = datetime.fromisoformat(work_data.get('start_date')) if work_data.get('start_date') else None
                work.end_date = datetime.fromisoformat(work_data.get('end_date')) if work_data.get('end_date') else None
        else:
            work = WorkExperience(
                user_id=user.id,
                company=work_data.get('company'),
                role_title=work_data.get('role_title'),
                job_description=work_data.get('job_description'),
                start_date=datetime.fromisoformat(work_data.get('start_date')) if work_data.get('start_date') else None,
                end_date=datetime.fromisoformat(work_data.get('end_date')) if work_data.get('end_date') else None
            )
            user.work_experience.append(work)

    # Update licenses and certifications
    licenses_certifications_data = data.get('licenses_certifications', [])
    for license_data in licenses_certifications_data:
        license_id = license_data.get('id')
        if license_id:
            license = LicenseCertification.query.get(license_id)
            if license and license.user_id == user.id:
                license.name = license_data.get('name', license.name)
                license.issuing_organization = license_data.get('issuing_organization', license.issuing_organization)
                license.issue_date = datetime.fromisoformat(license_data.get('issue_date')) if license_data.get('issue_date') else None
                license.expiration_date = datetime.fromisoformat(license_data.get('expiration_date')) if license_data.get('expiration_date') else None
                license.credentials_id = license_data.get('credentials_id', license.credentials_id)
                license.credential_url = license_data.get('credential_url', license.credential_url)
        else:
            license = LicenseCertification(
                user_id=user.id,
                name=license_data.get('name'),
                issuing_organization=license_data.get('issuing_organization'),
                issue_date=datetime.fromisoformat(license_data.get('issue_date')) if license_data.get('issue_date') else None,
                expiration_date=datetime.fromisoformat(license_data.get('expiration_date')) if license_data.get('expiration_date') else None,
                credentials_id=license_data.get('credentials_id'),
                credential_url=license_data.get('credential_url')
            )
            user.licenses_certifications.append(license)

    db.session.commit()
    return jsonify({'message': 'User updated successfully'}), 200


# Profile code ends here



# Define upload directory# Define upload directory


# Function to get user ID (this is just a placeholder, replace with your actual implementation)
def get_user_id_somehow():
    # For demonstration purposes, let's assume the user ID is submitted in the request form
    user_id = request.form.get('user_id')  
    return user_id

# Route to handle profile image uploads
# Configure Cloudinary
cloudinary.config(
    cloud_name = "dkj6ipdd6",
    api_key = "921656148348163",
    api_secret = "kQvQY26E6yWqS46f38Bc8hSXJQw"
)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_IMAGE_SIZE = (1024, 1024)  # Maximum dimensions for the image

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def compress_image(image, max_size=MAX_IMAGE_SIZE):
    img = Image.open(image)
    img.thumbnail(max_size)
    img_io = io.BytesIO()
    img.save(img_io, format='JPEG', quality=85)
    img_io.seek(0)
    return img_io

@app.route('/upload_profile_image', methods=['POST'])
@jwt_required()
def upload_profile_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    # Compress the image
    compressed_image = compress_image(file)

    # Upload to Cloudinary
    try:
        upload_result = cloudinary.uploader.upload(compressed_image.getvalue())
        image_url = upload_result['secure_url']
    except Exception as e:
        return jsonify({'error': f'Failed to upload image to Cloudinary: {str(e)}'}), 500

    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user is None:
        return jsonify({'error': 'User not found'}), 404

    # Store the Cloudinary URL in the database
    user.profile_image = image_url
    db.session.commit()

    return jsonify({'message': 'Profile image uploaded successfully', 'image_url': image_url}), 200

  # Blog starts here
  # Blog model
class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subheading = db.Column(db.String(200), nullable=True)
    featured_image = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=True)
    minutes_read = db.Column(db.Integer, nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('blogs', lazy='dynamic'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

# Create a new blog post
@app.route('/blogs', methods=['POST'])
@jwt_required()
def create_blog():
    author_id = get_jwt_identity()
    
    data = request.get_json()
    title = data.get('title')
    subheading = data.get('subheading')
    featured_image = data.get('featured_image')
    content = data.get('content')
    category = data.get('category')
    minutes_read = data.get('minutes_read')
    
    if not title or not content:
        return jsonify({'error': 'Title and content are required'}), 400
    
    blog = Blog(
        title=title,
        subheading=subheading,
        featured_image=featured_image,
        content=content,
        category=category,
        minutes_read=minutes_read,
        author_id=author_id
    )
    
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
        'subheading': blog.subheading,
        'featured_image': blog.featured_image,
        'content': blog.content,
        'category': blog.category,
        'minutes_read': blog.minutes_read,
        'author': blog.author.full_name if blog.author else 'Unknown',
        'author_profile_image': blog.author.profile_image if blog.author else None,  # Updated this line
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
        'subheading': blog.subheading,
        'featured_image': blog.featured_image,
        'content': blog.content,
        'category': blog.category,
        'minutes_read': blog.minutes_read,
        'author': blog.author.full_name,
        'author_profile_image': blog.author.profile_image,  # Updated this line
        'date_created': blog.date_created
    }
    return jsonify(blog_data), 200


# Update a blog post
@app.route('/blogs/<int:blog_id>', methods=['PUT'])
@jwt_required()
def update_blog(blog_id):
    user_id = get_jwt_identity()
    
    blog = Blog.query.get(blog_id)
    if not blog:
        return jsonify({'error': 'Blog post not found'}), 404
    
    if blog.author_id != user_id:
        return jsonify({'error': 'Unauthorized to update this blog post'}), 403
    
    data = request.get_json()
    blog.title = data.get('title', blog.title)
    blog.subheading = data.get('subheading', blog.subheading)
    blog.featured_image = data.get('featured_image', blog.featured_image)
    blog.content = data.get('content', blog.content)
    blog.category = data.get('category', blog.category)
    blog.minutes_read = data.get('minutes_read', blog.minutes_read)
    
    db.session.commit()
    
    return jsonify({'message': 'Blog post updated successfully'}), 200

# Delete a blog post
@app.route('/blogs/<int:blog_id>', methods=['DELETE'])
@jwt_required()
def delete_blog(blog_id):
    user_id = get_jwt_identity()
    
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
@jwt_required()
def send_message():
    sender_id = get_jwt_identity()

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
@app.route('/messages', methods=['GET'])
@jwt_required()
def get_all_messages():
    user_id = get_jwt_identity()
    users_only = request.args.get('users_only', 'false').lower() == 'true'

    if users_only:
        # Query for unique users
        chat_users = db.session.query(User).distinct().join(
            Message, or_(
                (Message.sender_id == User.id) & (Message.recipient_id == user_id),
                (Message.recipient_id == User.id) & (Message.sender_id == user_id)
            )
        ).filter(User.id != user_id).all()

        users_data = [{
            'id': user.id,
            'full_name': user.full_name,
            'profile_image': user.profile_image
        } for user in chat_users]

        return jsonify(users_data), 200

    # Add a return for when `users_only` is False or not provided
    return jsonify({"message": "No users found"}), 200


@app.route('/messages/<int:other_user_id>', methods=['GET'])
@jwt_required()
def get_messages(other_user_id):
    user_id = get_jwt_identity()

    # Get messages between two users
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


@app.route('/chat-users', methods=['GET'])
@jwt_required()
def get_chat_users_list():
    current_user_id = get_jwt_identity()

    # Query for users who have exchanged messages with the current user
    chat_users = db.session.query(User).distinct().join(
        Message, or_(
            (Message.sender_id == User.id) & (Message.recipient_id == current_user_id),
            (Message.recipient_id == User.id) & (Message.sender_id == current_user_id)
        )
    ).filter(User.id != current_user_id).all()

    users_data = [{
        'id': user.id,
        'full_name': user.full_name,
        'profile_image': user.profile_image
    } for user in chat_users]

    return jsonify(users_data), 200
    # Existing code for full message data
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

    # Existing code for full message data
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
@jwt_required()
def mark_message_as_read(message_id):
    user_id = get_jwt_identity()

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
@jwt_required()
def upload_peer_review():
    submitter_id = get_jwt_identity()

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
@jwt_required()
def get_available_reviews(course_id):
    user_id = get_jwt_identity()

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
@jwt_required()
def download_review_document(review_id):
    review = PeerReview.query.get(review_id)
    if not review:
        return jsonify({'error': 'Review not found'}), 404

    return send_file(review.document_path, as_attachment=True)

# Submit a review
@app.route('/peer-review/submit/<int:review_id>', methods=['POST'])
@jwt_required()
def submit_review(review_id):
    reviewer_id = get_jwt_identity()

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
@jwt_required()
def get_my_submissions():
    user_id = get_jwt_identity()

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
    fullname = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    roles = db.relationship('Role', secondary='admin_roles', back_populates='admins')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'fullname': self.fullname or '',
            'email': self.email or '',
            'phone': self.phone or '',
            'roles': [{'id': role.id, 'name': role.name} for role in self.roles]
        }


# Role model
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    admins = db.relationship('Admin', secondary='admin_roles', back_populates='roles')


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

    try:
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        admin = Admin(username=username, password=hashed_password)
        db.session.add(admin)
        db.session.commit()

        # Generate JWT token with admin claim
        access_token = create_access_token(identity=username, additional_claims={'is_admin': True})

        return jsonify({
            'message': 'Admin created successfully',
            'access_token': access_token
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# Admin login
@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    admin = Admin.query.filter_by(username=username).first()

    if not admin or not check_password_hash(admin.password, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    access_token = create_access_token(identity=admin.id, additional_claims={'is_admin': True})
    return jsonify({'access_token': access_token}), 200

# Admin middleware
def admin_required():
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            try:
                claims = get_jwt()
                print(f"Debug - JWT claims: {claims}")  # Debug print
                
                if not isinstance(claims, dict):
                    print(f"Debug - claims is not a dict, it's a {type(claims)}")  # Debug print
                    return jsonify({"msg": "Invalid token structure"}), 422
                
                if not claims.get('is_admin', False):
                    return jsonify({"msg": "Admins only!"}), 403
                
                return fn(*args, **kwargs)
            except Exception as e:
                print(f"Debug - Exception in admin_required: {str(e)}")  # Debug print
                return jsonify({"msg": "An error occurred while processing the request"}), 500
        return decorator
    return wrapper

# Create role
@app.route('/admin/roles', methods=['POST'])
@admin_required()
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
@admin_required()
def delete_role(role_id):
    role = Role.query.get(role_id)
    if not role:
        return jsonify({'error': 'Role not found'}), 404

    db.session.delete(role)
    db.session.commit()

    return jsonify({'message': 'Role deleted successfully'}), 200


# New endpoint: Fetch all admins
@app.route('/admin/admins', methods=['GET'])
@admin_required()
def get_all_admins():
    admins = Admin.query.all()
    return jsonify([admin.to_dict() for admin in admins]), 200


# New endpoint: Fetch all roles
@app.route('/admin/roles', methods=['GET'])
@admin_required()
def get_all_roles():
    roles = Role.query.all()
    return jsonify([{'id': role.id, 'name': role.name} for role in roles]), 200


# New endpoint: Delete an admin
@app.route('/admin/admins/<int:admin_id>', methods=['DELETE'])
@admin_required()
def delete_admin(admin_id):
    admin = Admin.query.get(admin_id)
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    
    db.session.delete(admin)
    db.session.commit()
    
    return jsonify({'message': 'Admin deleted successfully'}), 200


# New endpoint: Assign role to admin
@app.route('/admin/assign-role', methods=['POST'])
@admin_required()
def assign_role_to_admin():
    data = request.get_json()
    admin_id = data.get('admin_id')
    role_id = data.get('role_id')
    
    if not admin_id or not role_id:
        return jsonify({'error': 'Admin ID and Role ID are required'}), 400
    
    admin = Admin.query.get(admin_id)
    role = Role.query.get(role_id)
    
    if not admin or not role:
        return jsonify({'error': 'Admin or Role not found'}), 404
    
    admin.roles.append(role)
    db.session.commit()
    
    return jsonify({'message': 'Role assigned to admin successfully'}), 200



    # New endpoint: Remove role from admin
@app.route('/admin/remove-role', methods=['POST'])
@admin_required()
def remove_role_from_admin():
    data = request.get_json()
    admin_id = data.get('admin_id')
    role_id = data.get('role_id')
    
    if not admin_id or not role_id:
        return jsonify({'error': 'Admin ID and Role ID are required'}), 400
    
    admin = Admin.query.get(admin_id)
    role = Role.query.get(role_id)
    
    if not admin or not role:
        return jsonify({'error': 'Admin or Role not found'}), 404
    
    if role in admin.roles:
        admin.roles.remove(role)
        db.session.commit()
        return jsonify({'message': 'Role removed from admin successfully'}), 200
    else:
        return jsonify({'error': 'Admin does not have this role'}), 400






# Create instructor
@app.route('/admin/instructors', methods=['POST'])
@admin_required()
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
@admin_required()
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
@admin_required()
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

    if not instructor or not check_password_hash(instructor.password, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    access_token = create_access_token(identity=instructor.id, additional_claims={'is_instructor': True})
    return jsonify({'access_token': access_token}), 200

# Assign role to user
@app.route('/admin/assign-role', methods=['POST'])
@admin_required()
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
@admin_required()
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
@admin_required()
def get_user_roles(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    roles = [{'id': role.id, 'name': role.name} for role in user.roles]
    return jsonify(roles), 200

# Get all users with their roles
@app.route('/admin/users-with-roles', methods=['GET'])
@admin_required()
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


from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os

@app.route('/user/posts', methods=['POST'])
@jwt_required()
def create_user_post():
    user_id = get_jwt_identity()

    title = request.form.get('title')
    executive_summary = request.form.get('executive_summary')
    subject = request.form.get('subject')
    doi_link = request.form.get('doi_link')
    video_link = request.form.get('video_link')

    if not title or not executive_summary or not subject:
        return jsonify({'error': 'Title, executive summary, and subject are required'}), 400

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
@jwt_required()
def get_user_posts():
    user_id = get_jwt_identity()

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
@jwt_required()
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

@app.route('/courses_for_follow', methods=['GET'])
@jwt_required()
def get_courses_for_follow():
    courses = Course.query.all()
    return jsonify([{'id': c.id, 'title': c.title} for c in courses]), 200

@app.route('/follow_course/<int:course_id>', methods=['POST'])
@jwt_required()
def follow_course(course_id):
    user_id = get_jwt_identity()

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
@jwt_required()
def unfollow_course(course_id):
    user_id = get_jwt_identity()

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
@jwt_required()
def get_followed_posts():
    user_id = get_jwt_identity()

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
@jwt_required()
def create_notification():
    user_id = get_jwt_identity()

    content = request.json.get('content')
    if not content:
        return jsonify({'error': 'Notification content is required'}), 400

    notification = Notification(user_id=user_id, content=content)
    db.session.add(notification)
    db.session.commit()

    return jsonify({'message': 'Notification created successfully', 'id': notification.id}), 201

@app.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    user_id = get_jwt_identity()

    notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).all()
    notifications_data = [{
        'id': notif.id,
        'content': notif.content,
        'is_read': notif.is_read,
        'created_at': notif.created_at
    } for notif in notifications]

    return jsonify(notifications_data), 200

@app.route('/notifications/<int:notification_id>/read', methods=['PUT'])
@jwt_required()
def mark_notification_as_read(notification_id):
    user_id = get_jwt_identity()

    notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404

    notification.is_read = True
    db.session.commit()

    return jsonify({'message': 'Notification marked as read'}), 200

@app.route('/notifications/<int:notification_id>', methods=['DELETE'])
@jwt_required()
def delete_notification(notification_id):
    user_id = get_jwt_identity()

    notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404

    db.session.delete(notification)
    db.session.commit()

    return jsonify({'message': 'Notification deleted successfully'}), 200

    #Chatgpt code
    

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message}
            ]
        )
        
        ai_message = response.choices[0].message['content']
        return jsonify({"response": ai_message})
    except Exception as e:
        return jsonify({"error": str(e)}), 500






if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

