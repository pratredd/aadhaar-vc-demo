import json

import identity.web
import qrcode
import requests
from flask import Flask, redirect, render_template, request, session, url_for

import app_config
from flask_session import Session

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
  return render_template(
      "login.html",
      version=__version__,
      **auth.log_in(
          scopes=app_config.SCOPE,  # Have user consent to scopes during log-in
          redirect_uri=url_for(
              "auth_response", _external=True
          ),  # Optional. If present, this absolute URL must match your app's redirect_uri registered in Azure Portal
      ),
      faber=("/faberagent"),
      alice=("/aliceagent"))


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
  return render_template('index.html',
                         user=auth.get_user(),
                         version=__version__)


@app.route("/call_downstream_api")
def call_downstream_api():
  token = auth.get_token_for_user(app_config.SCOPE)
  if "error" in token:
    return redirect(url_for("login"))
  # Use access token to call downstream api
  print(token)
  api_result = requests.get(
      app_config.ENDPOINT,
      headers={
          'Authorization': 'Bearer ' + token['access_token']
      },
      timeout=30,
  ).json()
  return render_template('display.html', result=api_result)


@app.route('/faberagent')
def faber_agent():
  return render_template('aadhaar_homepage.html',
                         createinvite="/create_invite",
                         publishschema="/publish_schema",
                         acceptrequest="/accept_request",
                         issuecredential="/issue_credentials")


@app.route('/aliceagent')
def alice_agent():
  return render_template('alice_homepage.html')


@app.route('/publish_schema')
def post_schema_api():
  payload = {
      "attributes": ["name", "mobile number", "mail", "address"],
      "schema_name": "aadharschema",
      "schema_version": "6.0"
  }
  url = "http://" + app.config["FABER_HOST"] + "/schemas"
  headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
  r = requests.post(url, data=json.dumps(payload), headers=headers)
  data = r.json()
  cred_url = "http://" + app.config["FABER_HOST"] + "/credential-definitions"
  payload_cred = {
      "schema_id": data['schema_id'],
      'agent': 'faber.agent.aadharschema'
  }
  r = requests.post(cred_url, data=json.dumps(payload_cred), headers=headers)
  return render_template('publish.html', result=r.json())


@app.route('/create_invite')
def create_invitation():
  url1 = "http://" + app.config["FABER_HOST"] + "/connections/create-invitation"
  headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
  payload1 = {}
  r1 = requests.post(url1, data=json.dumps(payload1), headers=headers)

  rjson1 = json.loads(r1.text)
  invitation = json.dumps(rjson1['invitation'])
  #retrieve the connection id from response
  rjson1['connection_id']
  print(rjson1)
  print(rjson1['invitation_url'])
  #print(r.text)
  img = qrcode.make(rjson1['invitation'])
  img.save("static/images/displayQrInvite.png")
  print(img)

  return render_template('invite.html', result1=invitation.replace("'", "\""))


@app.route('/aliceagent', methods=['POST'])
def receiveinvitation():
  #Alice recieves the invitation
  invitation2 = request.form['invitation']
  url2 = "http://" + app.config[
      "ALICE_HOST"] + "/connections/receive-invitation"
  headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
  payload2 = invitation2
  r2 = requests.post(url2, data=json.dumps(payload2), headers=headers)
  rjson2 = json.loads(r2.text)
  session['connectionid'] = rjson2['connection_id']
  print(rjson2)

  return render_template('receive.html',
                         result2=rjson2['connection_id'],
                         accept="/acceptinvitation")


@app.route('/acceptinvitation')
def acceptinvitation():
  conn_id = session.get('connectionid')
  url3 = "http://" + app.config[
      "ALICE_HOST"] + "/connections/" + conn_id + "/accept-invitation"
  headers = {'Accept': 'application/json'}
  payload3 = ''
  r3 = requests.post(url3, data=json.dumps(payload3), headers=headers)
  rjson3 = json.loads(r3.text)
  return render_template('request_sent.html',
                         result3=rjson3['state'],
                         login=("/login"))


@app.route('/accept_request')
def getacceptrequest():
  url4 = "http://" + app.config["FABER_HOST"] + "/connections?state=request"
  headers = {'Accept': 'application/json'}
  r4 = requests.get(url4, headers=headers)
  rjson4 = json.loads(r4.text)['results']
  first = rjson4[0]
  session['connectionid_req'] = first['connection_id']

  return render_template('accept_request.html',
                         result4=first['connection_id'],
                         accepted="/request_accepted")


@app.route('/request_accepted')
def requestaccepted():
  conn_id2 = session.get('connectionid_req')
  url5 = "http://" + app.config[
      "FABER_HOST"] + "/connections/" + conn_id2 + "/accept-request"
  headers = {'Accept': 'application/json'}
  payload5 = ''
  r5 = requests.post(url5, data=json.dumps(payload5), headers=headers)
  rjson5 = json.loads(r5.text)
  return render_template('request_accepted.html',
                         result5=rjson5['state'],
                         login=("/login"))


@app.route('/issue_credentials')
def issuecredential():
  conn_id3 = session.get('connectionid_req')
  print("conn_id3:", conn_id3)
  #issuer did
  url11 = "http://" + app.config["FABER_HOST"] + "/wallet/did/public"
  headers11 = {'Accept': 'text/plain'}
  r11 = requests.get(url11, headers=headers11)
  data11 = r11.json()['result']
  issuer_did = data11['did']
  print("issuer_did:", issuer_did)
  #schema id
  url12 = "http://" + app.config["FABER_HOST"] + "/schemas/created"
  headers12 = {'Accept': 'text/plain'}
  r12 = requests.get(url12, headers=headers12)
  data12 = r12.json()['schema_ids']
  schema_id = data12[0]
  print("schema_id:", schema_id)
  #credential definition id
  url13 = "http://" + app.config[
      "FABER_HOST"] + "/credential-definitions/created"
  headers13 = {'Accept': 'text/plain'}
  r13 = requests.get(url13, headers=headers13)
  data13 = r13.json()['credential_definition_ids']
  cred_def_id = data13[0]
  print("cred_def_id:", cred_def_id)

  #issuing credential
  url14 = "http://" + app.config["FABER_HOST"] + "/issue-credential-2.0/send"
  headers14 = {'Content-type': 'application/json', 'Accept': 'text/plain'}
  payload14 = {
      "auto_remove": 'true',
      "comment": "Issuing credentials",
      "connection_id": session.get('connectionid_req'),
      "credential_preview": {
          "@type":
          "issue-credential/2.0/credential-preview",
          "attributes": [{
              "name": "name",
              "value": "Alice Smith"
          }, {
              "name": "mobile number",
              "value": "1234567890"
          }, {
              "name": "mail",
              "value": "alice@gmail.com"
          }, {
              "name": "address",
              "value": "123 Main Street, Cambridge"
          }]
      },
      "filter": {
          "indy": {
              "cred_def_id": data13[0],
              "issuer_did": data11['did'],
              "schema_id": data12[0],
              "schema_issuer_did": data11['did'],
              "schema_name": "aadharschema",
              "schema_version": "6.0"
          }
      },
      "trace": "false"
  }
  r14 = requests.post(url14, data=json.dumps(payload14), headers=headers14)
  data14 = r14.json()

  #to confirm issuance (records)
  url15 = "http://" + app.config["FABER_HOST"] + "/issue-credential-2.0/records"
  headers15 = {'Accept': 'text/plain'}
  r15 = requests.get(url15, headers=headers15)
  data15 = r15.json()['results']
  session['cred_ex_id']=data15[0]['cred_ex_record']['cred_ex_id']
  return render_template('issue_cred.html',
                         result=data15[0]['cred_ex_record']['state'],
                         result1=data15[1]['cred_ex_record']['cred_proposal']
                         ['credential_preview']['attributes'], result2=data15[0]['cred_ex_record']['cred_ex_id'])


if __name__ == "__main__":
  app.run(host='0.0.0.0', debug=True)
