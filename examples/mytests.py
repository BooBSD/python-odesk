"""
Python bindings to odesk API
python-odesk version 0.1
(C) 2010 oDesk
"""
import odesk

PUBLIC_KEY = '60fc0fa3b1a62cb07768b3fa1c8e0f8d'
SECRET_KEY = 'de26b187fe20112c'


#TODO: Desktop app example (check if it's working at all - wasn't last time)

def web_based_app(public_key, secret_key):
    print "Emulating web-based app"
    #Instantiating a client without an auth token
    client = odesk.Client(public_key, secret_key)
    print "Please to this URL (authorize the app if necessary):"
    print client.auth.auth_url()
    print "After that you should be redirected back to your app URL with " + \
          "additional ?frob= parameter"
    frob = raw_input('Enter frob: ') 
    auth_token, user = client.auth.get_token(frob)
    print "Authenticated user:"
    print user
    #Instantiating a new client, now with a token. 
    #Not strictly necessary here (could just set `client.auth_token`), but 
    #typical for web apps, which wouldn't probably keep client instances 
    #between requests
    client = odesk.Client(public_key, secret_key, auth_token)
    print "HR: teams"
    print client.hr.get_teams()
    print "HR: teamusers"
    print client.hr.get_team_users('137373')
    
   

if __name__ == '__main__':
    public_key = PUBLIC_KEY or raw_input('Enter public key: ')
    secret_key = SECRET_KEY or raw_input('Enter secret key: ')

    web_based_app(public_key, secret_key)

