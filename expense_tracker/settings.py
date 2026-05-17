from pathlib import Path
import os
from firebase_admin import credentials, initialize_app

# ------------------------------
# BASE DIR (Correct Way)
# ------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ------------------------------
# FIREBASE CONFIG
# ------------------------------
FIREBASE_KEY_PATH = os.path.join(BASE_DIR, "firebase", "serviceAccountKey.json")

cred = credentials.Certificate(FIREBASE_KEY_PATH)
firebase_app = initialize_app(cred)

# ------------------------------
# DJANGO SETTINGS
# ------------------------------
SECRET_KEY = "xyz"
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'expenses',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = "expense_tracker.urls"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, "templates")],  # FIXED
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = "expense_tracker.wsgi.application"

# ------------------------------
# DATABASE (DEFAULT)
# ------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, "db.sqlite3"),
    }
}

# ------------------------------
# STATIC FILES (FIXED)
# ------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static")  # FIXED
]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# ------------------------------
# DEFAULT PRIMARY KEY
# ------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# settings.py (Add to the end of the file)

# Auth Redirection Settings
LOGIN_URL = 'login'              # Redirects here if @login_required is triggered
LOGIN_REDIRECT_URL = 'home'      # Where to go after login
LOGOUT_REDIRECT_URL = 'first'    # Where to go after logout
