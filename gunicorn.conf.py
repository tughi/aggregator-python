import os

wsgi_app = f'''{os.getenv('FLASK_APP')}:create_app()'''

bind = '0.0.0.0:8000'

accesslog = '-'
errorlog = '-'
