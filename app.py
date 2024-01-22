import json

import identity.web
import qrcode
import requests
from flask import Flask, redirect, render_template, request, session, url_for,jsonify
from datetime import datetime

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
      aadhaar=("/aadhaaragent"),
      alice=("/aliceagent"),
      bank=("/bankagent"))


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


@app.route('/aadhaaragent')
def aadhar_agent():
  return render_template('aadhaar_homepage.html',
                         createinvite="/create_invite",
                         publishschema="/publish_schema",
                         acceptrequest="/accept_request",
                         issuecredential="/issue_credentials",
                        sendoffer="/send_offer")

# @app.route('/aliceagent')
# def alice_agent():
#   return render_template('alice_homepage.html',
#                          receiveinvite="/receive_invitation", viewcredential="/view_credential",
# sendpresentation="/sendpresentation")

@app.route('/bankagent')
def bank_agent():
    return render_template('bank_homepage.html',
                          presentreq="/presentation_req",
                          viewpresentation="/viewpresentation")
  
@app.route('/publish_schema')
def post_schema_api():
  payload = {
      "attributes": ["name", "mobile number", "mail", "address", "birthdate"],
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
  img = qrcode.make(rjson1['invitation_url'])
  img.save("static/images/displayQrInvite.png")
  print(img)

  return render_template('invite.html', result1=invitation.replace("'", "\""))

@app.route('/send_offer')
def send_offer():
  #connection_Id  
  url = "http://" + app.config["FABER_HOST"] + "/connections?state=active"
  headers = {'Accept': 'application/json'}
  r4 = requests.get(url, headers=headers)
  rjson = json.loads(r4.text)['results']
  first = rjson[0]
  session['connectionid'] = first['connection_id']
  conn_id = session.get('connectionid')
  print("conn_id:", conn_id)
  
  #credential definition Id
  cred_url = "http://" + app.config[
      "FABER_HOST"] + "/credential-definitions/created"
  cred_headers = {'Accept': 'text/plain'}
  cred_r = requests.get(cred_url, headers=cred_headers)
  cred_def_id = cred_r.json()['credential_definition_ids'][0]
  print("cred_def_id:", cred_def_id)

  #sending offer
  offer_url = "http://" + app.config["FABER_HOST"] + "/issue-credential/send-offer"
  offer_headers = {'Content-type': 'application/json'}
  offer_payload = {
    "auto_issue": "true",
    "auto_remove": "true",
    "comment": "string",
    "connection_id": conn_id,
    "cred_def_id": cred_def_id,
    "credential_preview": {
      "@type": "issue-credential/1.0/credential-preview",
      "attributes": [
                  {
                      "name": "name",
                      "value": "Alice Smith"
                  },
                  {
                      "name": "address",
                      "value": "house, street, city, state, country"
                  },
                  {
                      "name": "mail",
                      "value": "alice.smith@email.com"
                  },
                  {
                      "name": "mobile",
                      "value": "123456789"
                  },
                  {
                      "name": "birthdate",
                      "value": "1998-02-05"
                  }
              ]
    },
    "trace": "true"
  }

  offer_r = requests.post(offer_url,
                        data=json.dumps(offer_payload), 
                          headers=offer_headers)
  offer_data = offer_r.json()['state']
  print(offer_data)
  return render_template('send_offer.html', result=offer_data, login=("/login"))
  
# @app.route('/receive_invitation')
# def receive_inviteform():
#   return render_template('receive_invitation.html')
    
# @app.route('/receive_invitation', methods=['POST'])
# def receiveinvitation():
#   #Alice recieves the invitation
#   invitation2 = request.form['invitation']
#   url2 = "http://" + app.config[
#       "ALICE_HOST"] + "/connections/receive-invitation"
#   headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
#   payload2 = invitation2
#   r2 = requests.post(url2, data=json.dumps(payload2), headers=headers)
#   rjson2 = json.loads(r2.text)
#   session['connectionid'] = rjson2['connection_id']
#   print(rjson2)

#   return render_template('receive.html',
#                          result2=rjson2['connection_id'],
#                          accept="/acceptinvitation")


# @app.route('/acceptinvitation')
# def acceptinvitation():
#   conn_id = session.get('connectionid')
#   url3 = "http://" + app.config[
#       "ALICE_HOST"] + "/connections/" + conn_id + "/accept-invitation"
#   headers = {'Accept': 'application/json'}
#   payload3 = ''
#   r3 = requests.post(url3, data=json.dumps(payload3), headers=headers)
#   rjson3 = json.loads(r3.text)
#   return render_template('request_sent.html',
#                          result3=rjson3['state'],
#                          login=("/login"))


# @app.route('/accept_request')
# def getacceptrequest():
#   url4 = "http://" + app.config["FABER_HOST"] + "/connections?state=request"
#   headers = {'Accept': 'application/json'}
#   r4 = requests.get(url4, headers=headers)
#   rjson4 = json.loads(r4.text)['results']
#   first = rjson4[0]
#   session['connectionid_req'] = first['connection_id']

#   return render_template('accept_request.html',
#                          result4=first['connection_id'],
#                          name=first['their_label'],
#                          accepted="/request_accepted",
#                         login=("/login"))


# @app.route('/request_accepted')
# def requestaccepted():
#   conn_id2 = session.get('connectionid_req')
#   url5 = "http://" + app.config[
#       "FABER_HOST"] + "/connections/" + conn_id2 + "/accept-request"
#   headers = {'Accept': 'application/json'}
#   payload5 = ''
#   r5 = requests.post(url5, data=json.dumps(payload5), headers=headers)
#   rjson5 = json.loads(r5.text)
#   return render_template('request_accepted.html',
#                          result5=rjson5['state'],
#                          login=("/login"))


# @app.route('/issue_credentials')
# def issuecredential():
#   conn_id3 = session.get('connectionid_req')
#   print("conn_id3:", conn_id3)
#   #issuer did
#   url11 = "http://" + app.config["FABER_HOST"] + "/wallet/did/public"
#   headers11 = {'Accept': 'text/plain'}
#   r11 = requests.get(url11, headers=headers11)
#   data11 = r11.json()['result']
#   issuer_did = data11['did']
#   print("issuer_did:", issuer_did)
#   #schema id
#   url12 = "http://" + app.config["FABER_HOST"] + "/schemas/created"
#   headers12 = {'Accept': 'text/plain'}
#   r12 = requests.get(url12, headers=headers12)
#   data12 = r12.json()['schema_ids']
#   schema_id = data12[0]
#   print("schema_id:", schema_id)
#   #credential definition id
#   url13 = "http://" + app.config[
#       "FABER_HOST"] + "/credential-definitions/created"
#   headers13 = {'Accept': 'text/plain'}
#   r13 = requests.get(url13, headers=headers13)
#   data13 = r13.json()['credential_definition_ids']
#   session['cred_def_id'] = data13[0]
#   # print("cred_def_id:", session.get('cred_def_id')

#   #issuing credential
#   url14 = "http://" + app.config["FABER_HOST"] + "/issue-credential-2.0/send"
#   headers14 = {'Content-type': 'application/json', 'Accept': 'text/plain'}
#   payload14 = {
#       "auto_remove": 'true',
#       "comment": "Issuing credentials",
#       "connection_id": session.get('connectionid_req'),
#       "credential_preview": {
#           "@type":
#           "issue-credential/2.0/credential-preview",
#           "attributes": [{
#               "name": "name",
#               "value": "Alice Smith"
#           }, {
#               "name": "mobile_number",
#               "value": "1234567890"
#           }, {
#               "name": "mail",
#               "value": "alice@gmail.com"
#           }, {
#               "name": "address",
#               "value": "123 Main Street, Cambridge"
#           }]
#       },
#       "filter": {
#           "indy": {
#               "cred_def_id": data13[0],
#               "issuer_did": data11['did'],
#               "schema_id": data12[0],
#               "schema_issuer_did": data11['did'],
#               "schema_name": "aadhaar schema",
#               "schema_version": "18.6.95"
#           }
#       },
#       "trace": "false"
#   }
#   r14 = requests.post(url14, data=json.dumps(payload14), headers=headers14)
#   data14 = r14.json()
#   print(data14)
#   #to confirm issuance (records)
#   url15 = "http://" + app.config["FABER_HOST"] + "/issue-credential-2.0/records"
#   headers15 = {'Accept': 'text/plain'}
#   r15 = requests.get(url15, headers=headers15)
#   data15 = r15.json()['results']
#   session['cred_ex_id']=data15[0]['cred_ex_record']['cred_ex_id']
#   return render_template('issue_cred.html', login=("/login"),
#                          result=data15[0]['cred_ex_record']['state'],
#                          result2=data15[0]['cred_ex_record']['cred_ex_id'])

# @app.route('/view_credential')
# def viewcredential():
#   url16 = "http://" + app.config["ALICE_HOST"] + "/issue-credential-2.0/records"
#   headers16 = {'Accept': 'text/plain'}
#   r16 = requests.get(url16, headers=headers16)
#   cred_ex_id = r16.json()['results'][0]['cred_ex_record']['cred_ex_id']
#   print("cred_ex_id:", cred_ex_id)
#   #store credentials
#   url17 = "http://" + app.config[
#   "ALICE_HOST"] + "/issue-credential-2.0/records/" + cred_ex_id + "/store"
#   headers17 = {'Content-type': 'application/json', 'Accept': 'text/plain'}
#   payload17=''
#   r17 = requests.post(url17, data=json.dumps(payload17), headers=headers17)
#   data17=r17.json()
#   #fetch credentials
#   url18 = "http://" + app.config["ALICE_HOST"] + "/credentials"
#   headers18 = {'Accept': 'text/plain'}
#   r18 = requests.get(url18, headers=headers18)
#   attributes = r18.json()['results'][0]['attrs']
#   return render_template('view_cred.html', result=cred_ex_id, name = attributes.get("name"),
#      mail = attributes.get("mail"),
#     mobile_number = attributes.get("mobile_number"),
#     address = attributes.get("address"), login=("/login"))




@app.route('/presentation_req')
def presentation_req():
  cred_ex_id = session.get('cred_def_id')
  conn_id2 = session.get('connectionid')
  return render_template('presentation_req.html', cred_ex_id=cred_ex_id, 
                         conn_id=conn_id2)

@app.route('/presentation_req', methods=['POST'])
def presentationreq():
  input_payload = (request.form['request'])
  url19 = "http://" + app.config["FABER_HOST"] + "/present-proof/send-request"
  headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
  payload19 = json.loads(input_payload)
  r19 = requests.post(url19, data=json.dumps(payload19), headers=headers)
  rjson19 = json.loads(r19.text)['state']

  return render_template('send_presentation_req.html',
   result=rjson19,
   login=("/login"))


@app.route('/viewpresentation')
def viewpresentation():
  url20 = "http://" + app.config[
  "FABER_HOST"] + "/present-proof/records"
  headers20 = {'Content-type': 'application/json'}
  r20 = requests.get(url20, headers=headers20)
  state = r20.json()['results'][0]['state']
  r_mobile = r20.json()['results'][0]['presentation']['proof']['proofs'][0]['primary_proof']['ge_proofs'][0]['predicate']['value']
  r_name = r20.json()['results'][0]['presentation']['requested_proof']['revealed_attrs']['0_name_uuid']['raw']
  r_address = r20.json()['results'][0]['presentation']['requested_proof']['revealed_attrs']['0_address_uuid']['raw']
  r_mail = r20.json()['results'][0]['presentation']['requested_proof']['revealed_attrs']['0_mail_uuid']['raw']
#   pres_ex_id = r20.json()['results'][0]['pres_ex_id']
# #view presentation with pres_ex_id
#   url21 = "http://" + app.config[
#   "FABER_HOST"] + "/present-proof-2.0/records/" + pres_ex_id
#   headers21 = {'Content-type': 'application/json'}
#   r21 = requests.get(url21, headers=headers21)
#   r_name = r21.json()['by_format']['pres']['indy']['proof']['proofs'][0]['primary_proof']['eq_proof']['m']['name']

#   r_phone = r21.json()['by_format']['pres']['indy']['proof']['proofs'][0]['primary_proof']['eq_proof']['m']['mobile_number']
  
#   r_address = r21.json()['by_format']['pres']['indy']['proof']['proofs'][0]['primary_proof']['eq_proof']['revealed_attrs']['address']
  
#   r_mail = r21.json()['by_format']['pres']['indy']['proof']['proofs'][0]['primary_proof']['eq_proof']['revealed_attrs']['mail']
#   state = r21.json()['state']
  return render_template('view_presetation.html',
                         result=state, name=r_name,
                         mobile=r_mobile,
                         address=r_address,
                         mail=r_mail,
                         login=("/login"),
                        createaccount=("/createaccount"))

@app.route("/createaccount")
def createaccount():
  return render_template("account_created.html")

# @app.route("/sendpresentation")
# def sendpresentation():
#   url = "http://" + app.config["ALICE_HOST"] + "/credentials"
#   headers = {'Accept': 'text/plain'}
#   r = requests.get(url, headers=headers)
#   attributes = r.json()['results'][0]['attrs']
  
#   return render_template('send_presentation.html', name = attributes.get("name"),
#      mail = attributes.get("mail"),
#     mobile_number = attributes.get("mobile_number"),
#     address = attributes.get("address"), login=("/login"))

  
if __name__ == "__main__":
  app.run(host='0.0.0.0', debug=True)
