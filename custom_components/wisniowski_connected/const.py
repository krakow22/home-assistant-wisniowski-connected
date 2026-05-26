"""Constants for Wisniowski Connected."""

DOMAIN = "wisniowski_connected"

CLIENT_ID = "wisniowski-app"
INITIAL_BROKER_URL = "https://api.broker.lavva.cloud"
KEYCLOAK_TOKEN_URL = "https://sso.lavva.cloud/realms/lavva/protocol/openid-connect/token"
KEYCLOAK_AUTH_URL = "https://sso.lavva.cloud/realms/lavva/protocol/openid-connect/auth"
KEYCLOAK_USERINFO_URL = "https://sso.lavva.cloud/realms/lavva/protocol/openid-connect/userinfo"
REDIRECT_URI = "https://smart.wisniowski.pl/silent-check-sso.html"
INSTALLATION_SUBTYPE = "WISNIOWSKI"

CONF_AUTH_RESPONSE_URL = "auth_response_url"
CONF_BROKER_URL = "broker_url"
CONF_EXPIRES_AT = "expires_at"
CONF_INSTALLATION_ID = "installation_id"
CONF_REFRESH_EXPIRES_AT = "refresh_expires_at"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_REFRESH_TOKEN_UPDATED_AT = "refresh_token_updated_at"
CONF_TOKEN = "token"
CONF_USER_ID = "user_id"

DATA_CLIENT = "client"
DATA_COORDINATOR = "coordinator"
