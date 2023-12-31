import os

# Application (client) ID of app registration
CLIENT_ID = os.getenv("CLIENT_ID")
# Application's generated client secret: never check this into source control!
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# You can configure your authority via environment variable
# Defaults to a multi-tenant app in world-wide cloud
AUTHORITY = os.getenv("AUTHORITY", "https://login.microsoftonline.com/common")

REDIRECT_PATH = "/getAToken"  # Used for forming an absolute URL to your redirect URI.
# The absolute URL must match the redirect URI you set
# in the app's registration in the Azure portal.

# You can find more Microsoft Graph API endpoints from Graph Explorer
# https://developer.microsoft.com/en-us/graph/graph-explorer
ENDPOINT = 'https://graph.microsoft.com/v1.0/users'  # This resource requires no admin consent
#ENDPOINT = 'https://graph.microsoft.com/User.Read'  # This resource requires no admin consent

# You can find the proper permission names from this document
# https://docs.microsoft.com/en-us/graph/permissions-reference
SCOPE = ["User.Read"]

# Tells the Flask-session extension to store sessions in the filesystem
SESSION_TYPE = "filesystem"
# Using the file system will not work in most production systems,
# it's better to use a database-backed session store instead.

#host name for Agent
ISSUER_HOST = "http://ip172-18-0-87-cke3134snmng00flunog-8021.direct.labs.play-with-docker.com"

#host name for Faber Agent
FABER_HOST = os.getenv("FABER_IP")

#host name for Alice Agent
ALICE_HOST = os.getenv("ALICE_IP")
