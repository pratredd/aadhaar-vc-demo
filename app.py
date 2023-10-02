import identity.web
import requests
from flask import Flask, redirect, render_template, request, session, url_for
from flask_session import Session
import json
import qrcode
import app_config


__version__ = "0.7.0"  # The version of this sample, for troubleshooting purpose

app = Flask(__name__)
app.config.from_object(app_config)
assert app.config["REDIRECT_PATH"] != "/", "REDIRECT_PATH must not be /"
Session(app)

# This section is needed for url_for("foo", _external=True) to automatically
# generate http scheme when this sample is running on localhost,
# and to generate https scheme when it is deployed behind reversed proxy.
# See also https://flask.palletsprojects.com/en/2.2.x/deploying/proxy_fix/
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

auth = identity.web.Auth(
    session=session,
    authority=app.config["AUTHORITY"],
    client_id=app.config["CLIENT_ID"],
    client_credential=app.config["CLIENT_SECRET"],
)


@app.route("/login")
def login():
    return render_template("login.html", version=__version__, **auth.log_in(
        scopes=app_config.SCOPE, # Have user consent to scopes during log-in
        redirect_uri=url_for("auth_response", _external=True), # Optional. If present, this absolute URL must match your app's redirect_uri registered in Azure Portal
        ))


@app.route(app_config.REDIRECT_PATH)
def auth_response():
    result = auth.complete_log_in(request.args)
    if "error" in result:
        return render_template("auth_error.html", result=result)
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    return redirect(auth.log_out(url_for("index", _external=True)))


@app.route("/")
def index():
    if not (app.config["CLIENT_ID"] and app.config["CLIENT_SECRET"]):
        # This check is not strictly necessary.
        # You can remove this check from your production code.
        return render_template('config_error.html')
    if not auth.get_user():
        return redirect(url_for("login"))
    return render_template('index.html', user=auth.get_user(), version=__version__)


@app.route("/call_downstream_api")
def call_downstream_api():
    token = auth.get_token_for_user(app_config.SCOPE)
    if "error" in token:
        return redirect(url_for("login"))
    # Use access token to call downstream api
    print(token)
    api_result = requests.get(
        app_config.ENDPOINT,
        headers={'Authorization': 'Bearer ' + token['access_token']},
        timeout=30,
    ).json()
    return render_template('display.html', result=api_result)

@app.route('/publish_schema')
def post_schema_api():
    payload = {
        "attributes":[
            "name",
            "mobile number",
            "mail"
        ],
        "schema_name":"aadharschema",
        "schema_version":"6.0"
    }
    url="http://"+app.config["ISSUER_HOST"]+"/schemas"
    headers={'Content-type': 'application/json', 'Accept': 'text/plain'}
    r = requests.post(url, data=json.dumps(payload), headers=headers)
    data = r.json()
    cred_url = "http://"+app.config["ISSUER_HOST"]+"/credential-definitions"
    payload_cred = {
        "schema_id":data['schema_id'],
        'agent':'faber.agent.aadharschema'
    }
    r=requests.post(cred_url,data=json.dumps(payload_cred),headers=headers)
    return render_template('publish.html',result = r.json())

@app.route('/create_invite')
def create_invitation():
    url="http://"+app.config["ISSUER_HOST"]+"/connections/create-invitation"
    headers={'Content-type': 'application/json', 'Accept': 'application/json'}
    payload = {}
    r = requests.post(url,data=json.dumps(payload),headers=headers)
    rjson = json.loads(r.text) 
    #retrieve the connection id from response
    connId = rjson['connection_id']
    print(rjson)
    print(rjson['invitation_url'])
    #print(r.text)
    img = qrcode.make(rjson['invitation_url'])
    img.save("static/images/displayQrInvite.png")
    print(img)
    #faber accept the invitation
    #url="http://"+app.config["ISSUER_HOST"]+"/connections/"+connId+"/accept-invitation"
    #headers={'Accept': 'application/json'}
    #payload = {}
    #requests.post(url,data=json.dumps(payload),headers=headers)
    return render_template('invite.html',result = r.json())
    

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
