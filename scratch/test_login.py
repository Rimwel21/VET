from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app('default')
client = app.test_client()

u_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'

# Populate a session
client.get('/login')

with client.session_transaction() as sess:
    sess['_csrf_token'] = 'test_csrf_token'
    sess['ip'] = '127.0.0.1'
    sess['user_agent'] = u_agent

res = client.post(
    '/login',
    json={
        'email': 'adminvetclinic@gmail.com',
        'password': 'vetadminclinic1214'
    },
    headers={
        'X-CSRF-Token': 'test_csrf_token',
        'User-Agent': u_agent
    }
)

print('STATUS:', res.status_code)
print('BODY:', res.get_data(as_text=True))
