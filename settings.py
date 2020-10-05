from pathlib import Path
import psycopg2
import subprocess

testmode=0

# LINEbot
access_token = 'drl+7l75GhWk5Z0sxuNGWCSp274X4gCjrCiwFCRO++v+Pe3FPiH4CUUOrRFplDWPpw5lJxBVCpNsqEUOcq7UuAE5hF+CyXGC/WQQqYDV85U2NqcMpsyEGqJEvtOpn2PHC0pnp0rTk7jF71DmdSB2VwdB04t89/1O/w1cDnyilFU='
secret_key = '9e74e0d58f3bf175d8ba8b6be72beeca'

if testmode==1:
    db_info = 'postgres://zpzgwxpguilyyr:81ba89e775eec74ca0d1fda8d7b54ab2b64dafe0216bb8f2f7a18aab0cb6aa37@ec2-54-224-175-142.compute-1.amazonaws.com:5432/d6ncstig8dfmdl'
    DEBUG = True
else:
    proc = subprocess.Popen('printenv DATABASE_URL', stdout=subprocess.PIPE, shell=True)
    db_info = proc.stdout.read().decode('utf-8').strip()
    DEBUG = False

SQLALCHEMY_DATABASE_URI = db_info
SQLALCHEMY_TRACK_MODIFICATIONS = True
SWAGGER_UI_DOC_EXPANSION = 'list'
RESTPLUS_VALIDATE = True
JSON_AS_ASCII = False
UPLOADED_CONTENT_DIR = Path("upload")