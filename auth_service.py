import os
import getpass
import requests
import keyring
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("FIREBASE_API_KEY", "")
SERVICE_ID = "pyhabits_terminal"

class AuthService:
    def __init__(self):
        self.id_token = None
        self.local_id = None
        
    def _save_refresh_token(self, token):
        keyring.set_password(SERVICE_ID, "refresh_token", token)

    def _get_refresh_token(self):
        try:
            return keyring.get_password(SERVICE_ID, "refresh_token")
        except Exception:
            return None

    def login_with_email(self, email, password):
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        resp = requests.post(url, json=payload)
        data = resp.json()
        
        if "error" in data:
            raise Exception(data["error"]["message"])
            
        self.id_token = data["idToken"]
        self.local_id = data["localId"]
        self._save_refresh_token(data["refreshToken"])
        return True

    def login_with_google(self):
        import webbrowser
        import threading
        import json
        from http.server import BaseHTTPRequestHandler, HTTPServer

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <title>PyHabits CLI Login</title>
          <script type="module">
            import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
            import {{ getAuth, signInWithPopup, GoogleAuthProvider }} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";

            const firebaseConfig = {{
              apiKey: "{API_KEY}",
              authDomain: "{os.getenv('FIREBASE_PROJECT_ID', '')}.firebaseapp.com",
              projectId: "{os.getenv('FIREBASE_PROJECT_ID', '')}",
            }};

            const app = initializeApp(firebaseConfig);
            const auth = getAuth(app);
            const provider = new GoogleAuthProvider();

            window.onload = () => {{
              document.getElementById('status').innerText = 'Opening Google Sign-In...';
              signInWithPopup(auth, provider)
                .then((result) => {{
                  const user = result.user;
                  document.getElementById('status').innerText = 'Login successful! Sending to CLI...';
                  
                  user.getIdToken().then(idToken => {{
                     const payload = JSON.stringify({{
                         idToken: idToken,
                         refreshToken: user.refreshToken,
                         localId: user.uid
                     }});
                     fetch('/callback', {{
                        method: 'POST',
                        body: payload
                     }}).then(() => {{
                        document.getElementById('status').innerText = 'Success! You can close this window now and return to the terminal.';
                     }});
                  }});
                }}).catch((error) => {{
                  document.getElementById('status').innerText = 'Error: ' + error.message;
                }});
            }};
          </script>
        </head>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
          <h2>PyHabits CLI Login</h2>
          <p id="status">Loading...</p>
        </body>
        </html>
        """

        result_data = {}

        class AuthHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass
                
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))

            def do_POST(self):
                if self.path == '/callback':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode('utf-8'))
                    result_data['idToken'] = data.get('idToken')
                    result_data['refreshToken'] = data.get('refreshToken')
                    result_data['localId'] = data.get('localId')
                    
                    self.send_response(200)
                    self.send_header("Content-type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"OK")
                    
                    threading.Thread(target=self.server.shutdown).start()

        server = HTTPServer(('localhost', 8080), AuthHandler)
        print("[*] Opening your browser for Google Sign-In...")
        webbrowser.open('http://localhost:8080')
        server.serve_forever()

        if 'idToken' in result_data:
            self.id_token = result_data['idToken']
            self.local_id = result_data['localId']
            if result_data.get('refreshToken'):
                self._save_refresh_token(result_data['refreshToken'])
            return True
        return False


    def refresh_session(self):
        refresh_token = self._get_refresh_token()
        if not refresh_token:
            return False
            
        url = f"https://securetoken.googleapis.com/v1/token?key={API_KEY}"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        resp = requests.post(url, json=payload)
        data = resp.json()
        
        if "error" in data:
            return False
            
        self.id_token = data["id_token"]
        self.local_id = data["user_id"]
        # Save the new refresh token (it might be the same, but it's good practice)
        self._save_refresh_token(data["refresh_token"])
        return True

    def logout(self):
        self.id_token = None
        self.local_id = None
        try:
            keyring.delete_password(SERVICE_ID, "refresh_token")
        except Exception:
            pass

    def is_authenticated(self):
        return self.id_token is not None

# Global singleton instance
auth = AuthService()
