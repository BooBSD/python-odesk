"""
Python bindings to odesk API
python-odesk version 0.2
(C) 2010 oDesk
"""

VERSION = (0, 2, 0, 'beta', 1)

import urllib
from datetime import date


def get_version():
    version = '%s.%s' % (VERSION[0], VERSION[1])
    if VERSION[2]:
        version = '%s.%s' % (version, VERSION[2])
    if VERSION[3:] == ('alpha', 0):
        version = '%s pre-alpha' % version
    else:
        if VERSION[3] != 'final':
            version = "%s %s" % (version, VERSION[3])
            if VERSION[4] != 0:
                version = '%s %s' % (version, VERSION[4])
    return version

import urllib
import urllib2
import hashlib
import cookielib

try:
    import json
except ImportError:
    import simplejson as json

from odesk.utils import *


class HTTP400BadRequestError(urllib2.HTTPError):
    pass


class HTTP401UnauthorizedError(urllib2.HTTPError):
    pass


class HTTP403ForbiddenError(urllib2.HTTPError):
    pass


class HTTP404NotFoundError(urllib2.HTTPError):
    pass


class InvalidConfiguredException(Exception):
    pass


class APINotImplementedException(Exception):
    pass


class AuthenticationError(Exception):
    pass


class NotAuthenticatedError(Exception):
    pass


def signed_urlencode(secret, query={}):
    """
    Converts a mapping object to signed url query

    >>> signed_urlencode('some$ecret', {})
    'api_sig=5da1f8922171fbeffff953b773bcdc7f'
    >>> signed_urlencode('some$ecret', {'spam':42,'foo':'bar'})
    'api_sig=11b1fc2e6555297bdc144aed0a5e641c&foo=bar&spam=42'
    """
    message = secret
    for key in sorted(query.keys()):
        message += str(key) + str(query[key])
    query = query.copy()
    query['api_sig'] = hashlib.md5(message).hexdigest()
    return urllib.urlencode(query)


def raise_http_error(e):
    '''Raise custom exception'''
    if e.code == 400:
        raise HTTP400BadRequestError(e.filename, e.code, e.msg,
                                     e.hdrs, None)
    elif e.code == 401:
        raise HTTP401UnauthorizedError(e.filename, e.code, e.msg,
                                       e.hdrs, None)
    elif e.code == 403:
        raise HTTP403ForbiddenError(e.filename, e.code, e.msg,
                                    e.hdrs, None)
    elif e.code == 404:
        raise HTTP404NotFoundError(e.filename, e.code, e.msg,
                                   e.hdrs, None)
    else:
        raise e


class HttpRequest(urllib2.Request):
    """
    A hack around Request class that allows to specify HTTP method explicitly
    """

    def __init__(self, *args, **kwargs):
        #Request is an old-style class, so can't use `super`
        method = kwargs.pop('method', 'GET')
        urllib2.Request.__init__(self, *args, **kwargs)
        self.method = method

    def get_method(self):
        #FIXME: Http method hack. Should be removed once oDesk supports true
        #HTTP methods
        if self.method in ['PUT', 'DELETE']:
            return 'POST'
        #End of hack

        return self.method


class BaseClient(object):
    """
    A basic HTTP client which supports signing of requests as well
    as de-serializing of responses.
    """

    def __init__(self, public_key, secret_key, api_token=None):
        self.public_key = public_key
        self.secret_key = secret_key
        self.api_token = api_token

    def urlencode(self, data={}):
        data = data.copy()
        data['api_key'] = self.public_key
        if self.api_token:
            data['api_token'] = self.api_token
        return signed_urlencode(self.secret_key, data)

    def urlopen(self, url, data={}, method='GET'):
        data = data.copy()

        #FIXME: Http method hack. Should be removed once oDesk supports true
        #HTTP methods
        if method in ['PUT', 'DELETE']:
            data['http_method'] = method.lower()
        #End of hack

        self.last_method = method
        self.last_url = url
        self.last_data = data

        query = self.urlencode(data)

        if method == 'GET':
            url += '?' + query
            request = HttpRequest(url=url, data=None, method=method)
        else:
            request = HttpRequest(url=url, data=query, method=method)
        return urllib2.urlopen(request)

    def read(self, url, data={}, method='GET', format='json'):
        """
        Returns parsed Python object or raises an error
        """
        assert format == 'json', "Only JSON format is supported at the moment"
        url += '.' + format
        try:
            response = self.urlopen(url, data, method)
        except urllib2.HTTPError, e:
            raise_http_error(e)

        if format == 'json':
            result = json.loads(response.read())
        return result


class Client(BaseClient):
    """
    Main API client
    """

    def __init__(self, public_key, secret_key, api_token=None, format='json'):
        self.public_key = public_key
        self.secret_key = secret_key
        self.api_token = api_token
        self.format = format
        #Namespaces
        self.auth = Auth(self)
        self.team = Team(self)
        self.hr = HR2(self)
        self.provider = Provider(self)
        self.mc = Messages(self)
        self.time_reports = TimeReports(self)
        self.finreports = Finreports(self)
        self.otask = OTask(self)
        self.finance = Finance(self)
        self.ticket = Ticket(self)
        self.url = Url(self)
        self.oconomy = OConomy(self)

    #Shortcuts for HTTP methods
    def get(self, url, data={}):
        return self.read(url, data, method='GET', format=self.format)

    def post(self, url, data={}):
        return self.read(url, data, method='POST', format=self.format)

    def put(self, url, data={}):
        return self.read(url, data, method='PUT', format=self.format)

    def delete(self, url, data={}):
        return self.read(url, data, method='DELETE', format=self.format)
 

class Namespace(object):
    """
    A special 'proxy' class to keep API methods organized
    """

    base_url = 'https://www.odesk.com/api/'
    api_url = None
    version = 1

    def __init__(self, client):
        self.client = client

    def full_url(self, url):
        """
        Gets relative URL of API method and returns a full URL
        """
        return "%s%sv%d/%s" % (self.base_url, self.api_url, self.version, url)

    #Proxied client's methods
    def get(self, url, data={}):
        return self.client.get(self.full_url(url), data)

    def post(self, url, data={}):
        return self.client.post(self.full_url(url), data)

    def put(self, url, data={}):
        return self.client.put(self.full_url(url), data)

    def delete(self, url, data={}):
        return self.client.delete(self.full_url(url), data)


class Auth(Namespace):

    api_url = 'auth/'
    version = 1

    def auth_url(self, frob=None):
        """
        Returns authentication URL to be used in a browser
        In case of desktop (non-web) application a frob is required
        """
        data = {}
        if frob:
            data['frob'] = frob
        url = 'https://www.odesk.com/services/api/auth/?' + \
            self.client.urlencode(data)
        return url

    def get_frob(self):
        """
        Gets the frob for authentication
        """
        url = 'keys/frobs'
        result = self.post(url)
        return result['frob']

    def get_token(self, frob):
        """
        Gets authentication token
        """
        url = 'keys/tokens'
        result = self.post(url, {'frob': frob})
        #TODO: Maybe there's a better way to get user's info?
        return result['token'], result['auth_user']

    def check_token(self):
        """
        Check validity of authentication token
        """
        url = 'keys/token'
        result = self.get(url)
        return result['token'], result['auth_user']

    def revoke_token(self):
        """
        Revoke authentication token
        """
        url = 'keys/token'
        data = {'api_token': self.client.api_token,
                'api_key': self.client.public_key}
        return self.delete(url, data)
    
    
class Team(Namespace):

    api_url = 'team/'
    version = 1

    def get_teamrooms(self):
        """
        Retrieve all teamrooms accessible to the authenticated user
        """
        url = 'teamrooms'
        result = self.get(url)
        teamrooms = result['teamrooms']['teamroom']
        if not isinstance(teamrooms, list):
            teamrooms = [teamrooms]
        return teamrooms

    def get_snapshots(self, team_id, online='now'):
        """
        Retrieve team member snapshots

        Parameters:
          team_id   The Team ID
          online    'now' / 'last_24h' / 'all' (default 'now')
                    Filter for logged in users / users active in last 24 hours / all users
        """
        url = 'snapshots/%s' % team_id
        result = self.get(url, {'online': online})
        snapshots = result['teamroom']['snapshot']
        if not isinstance(snapshots, list):
            snapshots = [snapshots]
        return snapshots

    def get_snapshot(self, company_id, user_id, datetime=None):
        """
        Retrieve a company's user snapshots during given time or 'now'

        Parameters:
          company_id    The Company ID
          user_id       The User ID
          datetime      (default 'now') Timestamp either a datetime object 
                        or a string in ISO 8601 format (in UTC) yyyymmddTHHMMSSZ
                        or a string with UNIX timestamp (number of seconds after epoch)
        """
        url = 'snapshots/%s/%s' % (str(company_id), str(user_id))
        if datetime:   # date could be a list or a range also
            url += '/%s' % datetime.isoformat()
        result = self.get(url)
        snapshot = result['snapshot']
        return snapshot
    
    def update_snapshot(self, company_id, user_id, datetime=None, memo=''):
        """
        Update a company's user snapshot memo at given time or 'now'

        Parameters:
          company_id    The Company ID
          user_id       The User ID
          datetime      (default 'now') Timestamp either a datetime object 
                        or a string in ISO 8601 format (in UTC) yyyymmddTHHMMSSZ
                        or a string with UNIX timestamp (number of seconds after epoch)
          memo          The Memo text
        """
        url = 'snapshots/%s/%s' % (str(company_id), str(user_id))
        if datetime:
            url += '/%s' % datetime.isoformat()
        return self.post(url, {'memo':memo})

    def delete_snapshot(self, company_id, user_id, datetime=None):
        """
        Delete a company's user snapshot memo at given time or 'now'

        Parameters:
          company_id    The Company ID
          user_id       The User ID
          datetime      (default 'now') Timestamp either a datetime object 
                        or a string in ISO 8601 format (in UTC) yyyymmddTHHMMSSZ
                        or a string with UNIX timestamp (number of seconds after epoch)
        """
        url = 'snapshots/%s/%s' % (str(company_id), str(user_id))
        if datetime:
            url += '/%s' % datetime.isoformat()
        return self.delete(url)

    def get_workdiaries(self, team_id, username, date=None):
        """
        Retrieve a team member's workdiaries for given date or today

        Parameters:
          team_id       The Team ID
          username      The Team Member's username
          date          A datetime object or a string in yyyymmdd format (optional)
        """
        url = 'workdiaries/%s/%s' % (str(team_id), str(username))
        if date:
            url += '/%s' % str(date)
        result = self.get(url)
        snapshots = result.get('snapshots', {}).get('snapshot', [])
        if not isinstance(snapshots, list):
            snapshots = [snapshots]
        #not sure we need to return user
        return result['snapshots']['user'], snapshots

    def get_stream(self, team_id, user_id=None,\
                   from_ts=None):
        """
        get_stream(team_id, user_id=None, from_ts=None)
        """
        url = 'streams/%s' % (team_id)
        if user_id:
            url += '/%s' % (user_id)
        if from_ts:
            data = {'from_ts': from_ts}
        else:
            data = {}
        result = self.get(url, data)
        return result['streams']['snapshot']


class HR2(Namespace):
    """
    HRv2 API
    """
    api_url = 'hr/'
    version = 2

    '''user api'''

    def get_user(self, user_reference):
        """
        Retrieve the user object from the user reference

        Parameters:
          user_reference    The user reference
        """
        url = 'users/%s' % str(user_reference)
        result = self.get(url)
        return result['user']

    '''company api'''

    def get_companies(self):
        """
        Retrieves the list of companies to which the current authorized user has access
        """
        url = 'companies'
        result = self.get(url)
        return result['companies']

    def get_company(self, company_referece):
        """
        Retrieve the company object from the company reference

        Parameters:
          company_reference     The company reference (can be found using get_companies method)
        """
        url = 'companies/%s' % str(company_referece)
        result = self.get(url)
        return result['company']

    def get_company_teams(self, company_referece):
        """
        Retrieve a list of teams within the company being referenced
        (as long as the user has access to the referenced company) 

        Parameters
          company_reference     The company reference (can be found using get_companies method)
        """
        url = 'companies/%s/teams' % str(company_referece)
        result = self.get(url)
        return result['teams']

    def get_company_tasks(self, company_referece):
        """
        API doesn't support this call yet
        """
        raise APINotImplementedException("API doesn't support this call yet")

    def get_company_users(self, company_referece, active=True):
        """
        Retrieve a list of all users within the referenced company. 
        (only available for users with hiring privileges for the company)

        Parameters
          company_reference     The company reference (can be found using get_companies method)
          active                True/False (default True)
        """
        url = 'companies/%s/users' % str(company_referece)
        if active:
            data = {'status_in_company': 'active'}
        else:
            data = {'status_in_company': 'inactive'}
        result = self.get(url, data)
        return result['users']

    '''team api'''

    def get_teams(self):
        """
        Retrieve a list of all the teams that a user has acccess to.
        (this will return teams across all companies to which the current user has access)
        """
        url = 'teams'
        result = self.get(url)
        return result['teams']

    def get_team(self, team_reference, include_users=False):
        """
        Retrieve the team information

        Parameters
          team_reference    The team reference
          include_users     Whether to include details of users (default: False)
        """
        url = 'teams/%s' % str(team_reference)
        result = self.get(url, {'include_users': include_users})
        #TODO: check how included users returned
        return result['team']

    def get_team_tasks(self, team_reference):
        """
        API doesn't support this call yet
        """
        raise APINotImplementedException("API doesn't support this call yet")

    def get_team_users(self, team_reference, active=True):
        """
        get_team_users(team_reference, active=True)
        """
        url = 'teams/%s/users' % str(team_reference)
        if active:
            data = {'status_in_team': 'active'}
        else:
            data = {'status_in_team': 'inactive'}
        result = self.get(url, data)
        return result['users']

    def post_team_adjustment(self, team_reference, engagement_reference,
                             amount, comments, notes):
        '''
        Add bonus to an engagement

        Parameters
          team_reference        The Team reference
          engagement_reference  The Engagement reference
          amount                The adjustment/bonus amount
          comments              Comments
          notes                 Notes
        '''
        url = 'teams/%s/adjustments' % str(team_reference)
        data = {'engagement__reference': engagement_reference,
                'amount': amount,
                'comments': comments,
                'notes': notes}
        result = self.post(url, data)
        return result['adjustment']

    '''task api'''

    def get_tasks(self):
        "API doesn't support this call yet"
        raise APINotImplementedException("API doesn't support this call yet")

    '''userrole api'''

    def get_user_role(self, user_reference=None, team_reference=None, 
                      sub_teams=False):
        '''
        Retrieve a complete list of all roles the reference user 
        has within the referenced team/sub teams.

        Parameters
          user_reference    The User reference (optional: defaults to API user)
          team_reference    The team reference (optional)
          sub_teams         Whether to include sub team info (optional: defaults to False)
        '''
        data = {}
        if user_reference:
            data['user__reference'] = user_reference
        if team_reference:
            data['team__reference'] = team_reference
        data['include_sub_teams'] = sub_teams
        url = 'userroles'
        result = self.get(url, data)
        return result['userroles']

    '''job api'''

    def get_jobs(self, buyer_team_reference=None, include_sub_teams=False,
                 status=None, created_by=None, created_time_from=None,
                 created_time_to=None, page_offset=0, page_size=20, order_by=None):
        """
        Retrieves all jobs that a user has manage_recruiting accesss to.
        This API call can be used to find the reference ID of a specific jobi
        
        Parameters
          buyer_team_reference  (optional)
          include_sub_teams     (optional: defaults to False)
          status                (optional)
          created_by            Creator's user_id (optional)
          created_time_from     timestamp (optional)
          created_time_to       timestamp (optional)
          page_offset           Number of entries to skip (optional)
          page_size             Page size in number of entries (optional: default 20)
          order_by              (optional)
        """
        url = 'jobs'
        
        data = {}
        if buyer_team_reference:
            data['buyer_team__reference'] = buyer_team_reference
        
        data['include_sub_teams'] = False
        if include_sub_teams:
            data['include_sub_teams'] = include_sub_teams            
        
        if status:
            data['status'] = status            

        if created_by:
            data['created_by'] = created_by            

        if created_time_from:
            data['created_time_from'] = created_time_from            
            
        if created_time_to:
            data['created_time_to'] = created_time_to            
                                                        
        data['page'] = '%d;%d' % (page_offset, page_size)

        if order_by is not None:
            data['order_by'] = order_by

        result = self.get(url, data)
        return result['jobs']

    def get_job(self, job_reference):
        """
        Retrieve the complete job object for the referenced job.
        This is only available to users with manage_recruiting permissions 
        within the team that the job is posted in.

        Parameters
          job_reference     Job reference
        """
        url = 'jobs/%s' % str(job_reference)
        result = self.get(url)
        return result['job']

    def post_job(self, job_data):
        """
        Post a job

        Parameters
          job_data      Details of the job
        """
        url = 'jobs'
        result = self.post(url, {'job_data': job_data})
        return result
        
    def update_job(self, job_id, job_data):
        """
        Update a job

        Parameters
          job_id        Job reference
          job_data      New details of the job
        """
        url = 'jobs/%s' % str(job_id)
        return self.put(url, {'job_data': job_data})

    def delete_job(self, job_id, reason_code):
        """
        Delete a job

        Parameters
          job_id        Job reference
          readon_code   The reason code
        """
        url = 'jobs/%s' % str(job_id)
        return self.delete(url, {'reason_code': reason_code})

    '''offer api'''

    def get_offers(self, buyer_team_reference=None, status=None, job_ref=None, 
                   buyer_ref=None, provider_ref=None, agency_ref=None, 
                   created_time_from=None, created_time_to=None,
                   page_offset=0, page_size=20, order_by=None):
        """
        Retrieve a list of all the offers on a specific job or within a specific team

        Parameters
          buyer_team_reference  The team reference (optional)
          status                active/filled (optional: defaults to active)
          job_ref               The job reference (optional)
          buyer_ref             (optional)
          provider_ref          (optional)
          agency_ref            (optional)
          created_time_from     timestamp e.g.'2008-09-09 00:00:01' (optional)
          created_time_to       timestamp e.g.'2008-09-09 00:00:01' (optional)
          page_offset           Number of entries to skip (optional)
          page_size             Page size in number of entries (optional: default 20)
          order_by              (optional)
        """
        url = 'offers'
        data = {}
        if buyer_team_reference:
            data['buyer_team__reference'] = buyer_team_reference
        
        if status:
            data['status'] = status            

        if job_ref:
            data['job_ref'] = job_ref     

        if buyer_ref:
            data['buyer_ref'] = buyer_ref 
            
        if provider_ref:
            data['provider_ref'] = provider_ref    
            
        if agency_ref:
            data['agency_ref'] = agency_ref                                                 

        if created_time_from:
            data['created_time_from'] = created_time_from            
            
        if created_time_to:
            data['created_time_to'] = created_time_to        
                    
        data['page'] = '%d;%d' % (page_offset, page_size)

        if order_by is not None:
            data['order_by'] = order_by

        result = self.get(url, data)
        return result['offers']

    def get_offer(self, offer_reference):
        """
        Retrieve the referenced offer

        Parameters
          offer_reference   Offer reference
        """
        url = 'offers/%s' % str(offer_reference)
        result = self.get(url)
        return result['offer']

    '''engagement api'''

    def get_engagements(self, buyer_team_reference=None, include_sub_teams=False,
                 status=None, provider_ref=None, agency_ref=None, 
                 created_time_from=None, created_time_to=None,
                 page_offset=0, page_size=20, order_by=None):
        """
        Retrieve engagements

        Parameters
          buyer_team_reference  The team reference (optional)
          include_sub_teams     (optional: default False)
          status                active/filled (optional: defaults to active)
          provider_ref          (optional)
          agency_ref            (optional)
          created_time_from     timestamp e.g.'2008-09-09 00:00:01' (optional)
          created_time_to       timestamp e.g.'2008-09-09 00:00:01' (optional)
          page_offset           Number of entries to skip (optional)
          page_size             Page size in number of entries (optional: default 20)
          order_by              (optional)
        """
        url = 'engagements'
        
        data = {}
        if buyer_team_reference:
            data['buyer_team__reference'] = buyer_team_reference
        
        data['include_sub_teams'] = False
        if include_sub_teams:
            data['include_sub_teams'] = include_sub_teams            
        
        if status:
            data['status'] = status            

        if provider_ref:
            data['provider_ref'] = provider_ref 

        if agency_ref:
            data['agency_ref'] = agency_ref           

        if created_time_from:
            data['created_time_from'] = created_time_from            
            
        if created_time_to:
            data['created_time_to'] = created_time_to           
        
        data['page'] = '%d;%d' % (page_offset, page_size)

        if order_by is not None:
            data['order_by'] = order_by

        result = self.get(url, data)
        return result['engagements']

    def get_engagement(self, engagement_reference):
        """
        Retrieve referenced engagement

        Parameters
          engagement_reference
        """
        url = 'engagements/%s' % str(engagement_reference)
        result = self.get(url)
        return result['engagement']

    '''candidacy api'''

    def get_candidacy_stats(self):
        """
        Retrieve candidacy stats
        """
        url = 'candidacies/stats'
        result = self.get(url)
        return result['candidacy_stats']


class Provider(Namespace):
    api_url = 'profiles/'
    version = 1

    resume_info_result_keys={'otherexp':'experiences',
                             'skills':'skills',
                             'tests':'tests',
                             'certificates':'certificates',
                             'employments':'employments',
                             'educations':'educations',
                             'projects':'projects',
                             'quickinfo':'quick_info'
                             }

    def get_provider(self, provider_ciphertext):
        """
        Retrieve an exhastive list of atributes associated with the referenced provider

        Parameters
          provider_ciphertext   The provider's cipher text (key)
        """
        url = 'providers/%s' % str(provider_ciphertext)
        result = self.get(url)
        return result['profile']

    def get_provider_brief(self, provider_ciphertext):
        """
        Retrieve an brief list of atributes associated with the referenced provider

        Parameters
          provider_ciphertext   The provider's cipher text (key)
        """
        url = 'providers/%s/brief' % str(provider_ciphertext)
        result = self.get(url)
        return result['profile']

    def get_providers(self, data=None, page_offset=0, page_size=20, order_by=None):
        """
        Search oDesk providers

        Parameters
          data          A dict (q:query, c1:Job Category, c2:Secondary Category, 
                        fb:Feedback, hrs:Hours, ir:Is Recent, min:Min Hourly Rate,
                        max:Max Hourly Rate, loc:Location, pt:Provider Type, 
                        last:Last Activity, test:Test, port:Total Portfolio Items,
                        rdy:Is oDesk Ready, ui:English Skills, ag:Agency,
                        to:Titles Only, g:Group Member)
          page_offset   Start of page (number of results to skip) (optional)
          page_size     Page size (number of results) (optional: default 20)
          order_by
        """
        url = 'search/providers'
        if data is None:
            data = {}     # shouldn't use data={} as default arg value (mutations persist throughout calls)
        data['page'] = '%d;%d' % (page_offset, page_size)
        if order_by is not None:
            data['order_by'] = order_by
        result = self.get(url, data=data)
        return result['providers']

    def get_jobs(self, data=None, page_offset=0, page_size=20, order_by=None):
        """
        Search oDesk jobs

        Parameters
          data          A dict (q:query, c1:Job Category, c2:Secondary Category, 
                        fb:Feedback, min:Min Budget, max:Max Budget, t:Job Type,
                        wl:Hours/Week, dur:Duration of Engagement, dp:Date Posted,
                        st:Status for Search, tba:Total Billed Assignments,
                        gr:Pref Group, to:Titles Only)
          page_offset   Start of page (number of results to skip) (optional)
          page_size     Page size (number of results) (optional: default 20)
          order_by
        """
        url = 'search/jobs'
        if data is None:
            data = {}     # shouldn't use data={} as default arg value (mutations persist throughout calls)
        data['page'] = '%d;%d' % (page_offset, page_size)
        if order_by is not None:
            data['order_by'] = order_by
        result = self.get(url, data=data)
        return result['jobs']

    def _get_resume_info(self, provider_ciphertext, info_type):
        '''
        info_type can be one of 
        (otherexp|skills|tests|certificates|employments|\
        educations|projects)
        '''
        strinfo = str(info_type)
        if strinfo not in self.resume_info_result_keys:
            raise ValueError('invalid info_type %s' % strinfo)
        url = 'providers/%s/%s' % (str(provider_ciphertext), strinfo)
        result = self.get(url)
        result_key = self.resume_info_result_keys[strinfo]
        return result[result_key]

    def _add_resume_info_item(self, provider_ciphertext, info_type,\
        item_data):
        '''
        info_type can be one of 
        (otherexp|skills|tests|certificates|employments|\
        educations|projects
        '''
        strinfo = str(info_type)
        if strinfo not in self.resume_info_result_keys:
            raise ValueError('invalid info_type %s' % strinfo)
        url = 'providers/%s/%s' % (str(provider_ciphertext), strinfo)
        return self.post(url, item_data)

    def _update_resume_info_item(self, provider_ciphertext,\
        resource_id, info_type, item_data):
        '''
        info_type can be one of (otherexp|skills|tests|certificates|\
        employments|educations|projects
        '''
        strinfo = str(info_type)
        if strinfo not in self.resume_info_result_keys:
            raise ValueError('invalid info_type %s' % strinfo)

        if resource_id is not None:
            url = 'providers/%s/%s/%s' % (str(provider_ciphertext),\
                str(resource_id), strinfo)
        else:
            url = 'providers/%s/%s' % (str(provider_ciphertext),\
                strinfo)
        return self.post(url, item_data)

    def _delete_resume_info_item(self, provider_ciphertext,\
        resource_id, info_type):
        '''
        info_type can be one of (otherexp|skills|tests|certificates|\
        employments|educations|projects
        '''
        strinfo = str(info_type)
        if strinfo not in self.resume_info_result_keys:
            raise ValueError('invalid info_type %s' % strinfo)

        if resource_id is not None:
            url = 'providers/%s/%s/%s' % (str(provider_ciphertext),\
                str(resource_id), strinfo)
        else:
            url = 'providers/%s/%s' % (str(provider_ciphertext),\
                strinfo)

        return self.delete(url)

    def get_skills(self, provider_ciphertext):
        """
        Retrieve provider skills info

        Parameters
          provider_ciphertext   Provider cipher text (key)
        """
        return self._get_resume_info(provider_ciphertext, 'skills')

    def add_skill(self, provider_ciphertext, data):
        """
        Add provider skills info

        Parameters
          provider_ciphertext   Provider cipher text (key)
          data                  dict containing details of skill to add
          """
        return self._add_resume_info_item(provider_ciphertext,\
            'skills', data)

    def update_skill(self, provider_ciphertext, skill_id, data):
        """
        Update provider skills info

        Parameters
          provider_ciphertext   Provider cipher text (key)
          skill_id              Resource id of the referenced skill
          data                  dict containing details of skill to delete
          """        
        return self._update_resume_info_item(provider_ciphertext,\
            skill_id, 'skills', data)

    def delete_skill(self, provider_ciphertext, skill_id):
        """
        Delete provider skills info

        Parameters
          provider_ciphertext   Provider cipher text (key)
          skill_id              Resource id of the referenced skill
          """
        return self._delete_resume_info_item(provider_ciphertext,\
            skill_id, 'skills')
    
    def get_quickinfo(self, provider_ciphertext):
        """
        Retrieve provider 'quick info'

        Parameters
          provider_ciphertext   Provider cipher text (key)
        """
        return self._get_resume_info(provider_ciphertext, 'quickinfo')

    def update_quickinfo(self, provider_ciphertext, data):
        """
        Update provider 'quick info'

        Parameters
          provider_ciphertext   Provider cipher text (key)
          data                  A dict containing updated 'quick info'
        """
        return self._update_resume_info_item(provider_ciphertext, None,\
                                            'quickinfo', data)

    def get_affiliates(self, affiliate_key):
        """
        Retrieve provider affiliates

        Parameters
          affiliate_key
        """
        url = 'affiliates/%s' % affiliate_key
        result = self.get(url)
        return result['profile']


class Messages(Namespace):
    api_url = 'mc/'
    version = 1

    def get_trays(self, username=None, paging_offset=0, paging_count=20):
        """
        Retrieve a list of all active trays and a message count for each

        Parameters
          username          User name
        """
        url = 'trays'
        if paging_offset or not paging_count == 20:
            data = {'paging': '%s;%s' % (str(paging_offset),
                                         str(paging_count))}
        else:
            data = {}

        if username:
            url += '/%s' % str(username)
        result = self.get(url, data=data)
        return result["trays"]

    def get_tray_content(self, username, tray, paging_offset=0,
                         paging_count=20):
        """
        Retrieve tray contents

        Parameters
          username          User name
          tray              Tray
          paging_offset     Start of page (number of results to skip)
          paging_count      Page size (number of results)
        """
        url = 'trays/%s/%s' % (str(username), str(tray))
        if paging_offset or not paging_count == 20:
            data = {'paging': '%s;%s' % (str(paging_offset),
                                         str(paging_count))}
        else:
            data = {}

        result = self.get(url, data=data)
        return result["current_tray"]["threads"]

    def get_thread_content(self, username, thread_id, paging_offset=0,
                           paging_count=20):
        """
        List details of a specific thread

        Parameters
          username          User name
          thread_id         Thread ID
          paging_offset     Start of page (number of results to skip)
          paging_count      Page size (number of results)
        """
        url = 'threads/%s/%s' % (str(username), (thread_id))
        if paging_offset or not paging_count == 20:
            data = {'paging': '%s;%s' % (str(paging_offset),
                                         str(paging_count))}
        else:
            data = {}

        result = self.get(url, data=data)
        return result["thread"]

    def _generate_many_threads_url(self, url, threads_ids):
        return ';'.join(urllib.quote(str(i)) for i in threads_ids)

    def put_threads_read_unread(self, username, thread_ids, read=True):
        """
        Marks threads as read/unread

        Parameters
          username          User name
          thread_ids        must be a list, even of 1 item
          read              True/False (optional: default True)
        """
        url = 'threads/%s/' % str(username)
        if read:
            data = {'read': 'true'}
        else:
            data = {'read': 'false'}
        result = self.put(self._generate_many_threads_url(url,\
                            thread_ids), data=data)
        return result

    def put_threads_read(self, username, thread_ids):
        """
        Marks threads as read

        Parameters
          username          User name
          thread_ids        must be a list, even of 1 item
        """
        return self.put_threads_read_unread(username, thread_ids, read=True)

    def put_threads_unread(self, username, thread_ids):
        """
        Marks threads as unread

        Parameters
          username          User name
          thread_ids        must be a list, even of 1 item
        """
        return self.put_threads_read_unread(username, thread_ids, read=False)

    def put_threads_starred_or_unstarred(self, username, thread_ids,
                                         starred=True):
        """
        Marks threads as starred/not starred

        Parameters
          username          User name
          thread_ids        must be a list, even of 1 item
          starred           True/False (optional: default True)
        """
        url = 'threads/%s/' % str(username)

        if starred:
            data = {'starred': 'true'}
        else:
            data = {'starred': 'false'}

        result = self.put(self._generate_many_threads_url(url,\
                            thread_ids), data=data)
        return result

    def put_threads_starred(self, username, thread_ids):
        """
        Marks threads as starred

        Parameters
          username          User name
          thread_ids        must be a list, even of 1 item
        """
        return self.put_threads_starred_or_unstarred(username,
                                            thread_ids, starred=True)

    def put_threads_unstarred(self, username, thread_ids):
        """
        Marks threads as unstarred

        Parameters
          username          User name
          thread_ids        must be a list, even of 1 item
        """
        return self.put_threads_starred_or_unstarred(username,
                                            thread_ids, starred=False)

    def put_threads_deleted_or_undeleted(self, username, thread_ids,
                                         deleted=True):
        """
        Marks threads as deleted/not deleted

        Parameters
          username          User name
          thread_ids        must be a list, even of 1 item
          deleted           True/False (optional: default True)
        """
        url = 'threads/%s/' % str(username)

        if deleted:
            data = {'deleted': 'true'}
        else:
            data = {'deleted': 'false'}

        result = self.put(self._generate_many_threads_url(url, thread_ids),
                          data=data)
        return result

    def put_threads_deleted(self, username, thread_ids):
        """
        Marks threads as deleted

        Parameters
          username          User name
          thread_ids        must be a list, even of 1 item
        """
        return self.put_threads_deleted_or_undeleted(username, thread_ids,
                                                     deleted=True)

    def put_threads_undeleted(self, username, thread_ids):
        """
        Marks threads as not deleted

        Parameters
          username          User name
          thread_ids        must be a list, even of 1 item
        """
        return self.put_threads_deleted_or_undeleted(username, thread_ids,
                                                     deleted=False)

    def post_message(self, username, recipients, subject, body,
                     thread_id=None):
        """
        Send a new message (creating a new thread) or reply to an existing thread

        Parameters
          username      User name (of sender)
          recipients    Recipient(s)  (a single string or a list/tuple)
          subject       Message subject
          body          Message text
          thread_id     The thread id if replying to an existing thread (optional)
        """
        url = 'threads/%s' % str(username)
        if not isinstance(recipients, (list, tuple)):
            recipients = [recipients]
        recipients = ','.join(map(str, recipients))
        if thread_id:
            url += '/%s' % str(thread_id)
        result = self.post(url, data={'recipients': recipients,
                                      'subject': subject,
                                      'body': body})
        return result


class OTask(Namespace):
    api_url = 'otask/'
    version = 1

    def get_company_tasks(self, company_id):
        """
        Retrieve a list of all tasks assigned within a company
        The user authenticated must have been granted the appropriate 
        hiring manager permissions

        Parameters
          company_id    Company ID
        """
        url = 'tasks/companies/%s/tasks' % str(company_id)
        result = self.get(url)
        return result["tasks"] or []

    def get_team_tasks(self, company_id, team_id):
        """
        Retrieve a list of all tasks assigned to a team
        The user authenticated must have been granted the appropriate 
        hiring manager permissions

        Parameters
          company_id    Company ID
          team_id       Team ID
        """
        url = 'tasks/companies/%s/teams/%s/tasks' % (str(company_id),
                                                     str(team_id))
        result = self.get(url)
        return result["tasks"] or []

    def get_user_tasks(self, company_id, team_id, user_id):
        """
        Retrieve a list of all tasks assigned to a team member
        The user authenticated must have been granted the appropriate 
        hiring manager permissions

        Parameters
          company_id    Company ID
          team_id       Team ID
          user_id       User ID
        """
        url = 'tasks/companies/%s/teams/%s/users/%s/tasks' % (str(company_id),
                                                    str(team_id), str(user_id))
        result = self.get(url)
        return result["tasks"] or []

    def get_company_tasks_full(self, company_id):
        """
        Retrieve full list of all tasks assigned within a company (with detail 
        of level at which the task is assigned)
        The user authenticated must have been granted the appropriate 
        hiring manager permissions

        Parameters
          company_id    Company ID
        """
        url = 'tasks/companies/%s/tasks/full_list' % str(company_id)
        result = self.get(url)
        return result["tasks"] or []

    def get_team_tasks_full(self, company_id, team_id):
        """
        Retrieve a list of all tasks assigned to a team (with detail of level 
        at which the task is assigned)
        The user authenticated must have been granted the appropriate 
        hiring manager permissions

        Parameters
          company_id    Company ID
          team_id       Team ID
        """
        url = 'tasks/companies/%s/teams/%s/tasks/full_list' %\
                                             (str(company_id), str(team_id))
        result = self.get(url)
        return result["tasks"] or []

    def get_user_tasks_full(self, company_id, team_id, user_id):
        """
        Retrieve a list of all tasks assigned to a team member (with detail of 
        level at which the task is assigned)
        The user authenticated must have been granted the appropriate 
        hiring manager permissions

        Parameters
          company_id    Company ID
          team_id       Team ID
          user_id       User ID
        """
        url = 'tasks/companies/%s/teams/%s/users/%s/tasks/full_list' %\
                                (str(company_id), str(team_id), str(user_id))
        result = self.get(url)
        return result["tasks"] or []

    def _generate_many_tasks_url(self, task_codes):
        return ';'.join(urllib.quote(str(c)) for c in task_codes)

    def get_company_specific_tasks(self, company_id, task_codes):
        """
        Return a specific task record within a company

        Parameters
          company_id    Company ID
          task_codes    Task codes (must be a list, even of 1 item)
        """
        url = 'tasks/companies/%s/tasks/%s' % (str(company_id),
                                    self._generate_many_tasks_url(task_codes))
        result = self.get(url)
        return result["tasks"]

    def get_team_specific_tasks(self, company_id, team_id, task_codes):
        """
        Return a specific task record within a team

        Parameters
          company_id    Company ID
          team_id       Team ID
          task_codes    Task codes (must be a list, even of 1 item)
        """
        url = 'tasks/companies/%s/teams/%s/tasks/%s' %\
                                             (str(company_id), str(team_id),
                                    self._generate_many_tasks_url(task_codes))
        result = self.get(url)
        return result["tasks"] or []

    def get_user_specific_tasks(self, company_id, team_id, user_id,
                                task_codes):
        """
        Return a specific task record for a team member

        Parameters
          company_id    Company ID
          team_id       Team ID
          user_id       User ID
          task_codes    Task codes (must be a list, even of 1 item)
        """
        url = 'tasks/companies/%s/teams/%s/users/%s/tasks/%s' %\
                                (str(company_id), str(team_id), str(user_id),
                                 self._generate_many_tasks_url(task_codes))
        result = self.get(url)
        return result["tasks"] or []

    def post_company_task(self, company_id, code, description, url):
        """
        Create a company task
        The authenticated user needs to have hiring manager privileges

        Parameters
          company_id    Company ID
          code          Task code
          description   Task description
          url           Task URL
        """
        url = 'tasks/companies/%s/tasks' % str(company_id)
        data = {'code': code,
                'description': description,
                'url': url}
        result = self.post(url, data)
        return result

    def post_team_task(self, company_id, team_id, code, description, url):
        """
        Create a team task
        The authenticated user needs to have hiring manager privileges

        Parameters
          company_id    Company ID
          team_id       Team ID
          code          Task code
          description   Task description
          url           Task URL
        """
        post_url = 'tasks/companies/%s/teams/%s/tasks' % (
            str(company_id), str(team_id))
        data = {'code': code,
                'description': description,
                'url': url}
        result = self.post(post_url, data)
        return result

    def post_user_task(self, company_id, team_id, user_id, code, description,
                       url):
        """
        Create a task assigned to self

        Parameters
          company_id    Company ID
          team_id       Team ID
          user_id       User ID
          code          Task code
          description   Task description
          url           Task URL
        """
        post_url = 'tasks/companies/%s/teams/%s/users/%s/tasks' % (
            str(company_id), str(team_id), str(user_id))
        data = {'code': code,
                'description': description,
                'url': url}
        result = self.post(post_url, data)
        return result

    def put_company_task(self, company_id, code, description, url):
        """
        Update a company task
        The authenticated user needs to have hiring manager privileges

        Parameters
          company_id    Company ID
          code          Task code
          description   Task description
          url           Task URL
        """
        put_url = 'tasks/companies/%s/tasks/%s' % (str(company_id), str(code))
        data = {'code': code,
                'description': description,
                'url': url}
        result = self.put(put_url, data)
        return result

    def put_team_task(self, company_id, team_id, code, description, url):
        """
        Update a team task
        The authenticated user needs to have hiring manager privileges

        Parameters
          company_id    Company ID
          team_id       Team ID
          code          Task code
          description   Task description
          url           Task URL
        """
        put_url = 'tasks/companies/%s/teams/%s/tasks/%s' % (
            str(company_id), str(team_id), str(code))
        data = {'code': code,
                'description': description,
                'url': url}
        result = self.put(put_url, data)
        return result

    def put_user_task(self, company_id, team_id, user_id, code,
                      description, url):
        """
        Update a task assigned to self

        Parameters
          company_id    Company ID
          team_id       Team ID
          user_id       User ID
          code          Task code
          description   Task description
          url           Task URL
        """
        put_url = 'tasks/companies/%s/teams/%s/users/%s/tasks/%s' % (
            str(company_id), str(team_id), str(user_id), str(code))
        data = {'code': code,
                'description': description,
                'url': url}
        result = self.put(put_url, data)
        return result

    def delete_company_task(self, company_id, task_codes):
        """
        Delete specific tasks within a company

        Parameters
          company_id    Company ID
          task_codes    Task codes (must be a list, even of 1 item)
        """
        url = 'tasks/companies/%s/tasks/%s' % (str(company_id),
                                    self._generate_many_tasks_url(task_codes))
        return self.delete(url, {})

    def delete_team_task(self, company_id, team_id, task_codes):
        """
        Delete specific tasks within a team

        Parameters
          company_id    Company ID
          team_id       Team ID
          task_codes    Task codes (must be a list, even of 1 item)
        """
        url = 'tasks/companies/%s/teams/%s/tasks/%s' % (str(company_id),
                    str(team_id), self._generate_many_tasks_url(task_codes))
        return self.delete(url, {})

    def delete_user_task(self, company_id, team_id, user_id, task_codes):
        """
        Delete specific tasks assigned to a team member

        Parameters
          company_id    Company ID
          team_id       Team ID
          user_id       User ID
          task_codes    Task codes (must be a list, even of 1 item)
        """
        url = 'tasks/companies/%s/teams/%s/users/%s/tasks/%s' %\
                                 (str(company_id), str(team_id), str(user_id),
                                 self. _generate_many_tasks_url(task_codes))
        return self.delete(url, {})

    def delete_all_company_tasks(self, company_id):
        """
        Delete all tasks within a company

        Parameters
          company_id    Company ID
          task_codes    Task codes (must be a list, even of 1 item)
        """
        url = 'tasks/companies/%s/tasks/all_tasks' % (str(company_id))
        return self.delete(url, {})

    def delete_all_team_tasks(self, company_id, team_id):
        """
        Delete all tasks within a team

        Parameters
          company_id    Company ID
          team_id       Team ID
          task_codes    Task codes (must be a list, even of 1 item)
        """
        url = 'tasks/companies/%s/teams/%s/tasks/all_tasks' % (str(company_id),
                                                      str(team_id))
        return self.delete(url, {})

    def delete_all_user_tasks(self, company_id, team_id, user_id):
        """
        Delete all tasks assigned to a team member

        Parameters
          company_id    Company ID
          team_id       Team ID
          user_id       User ID
          task_codes    Task codes (must be a list, even of 1 item)
        """
        url = 'tasks/companies/%s/teams/%s/users/%s/tasks/all_tasks' %\
                     (str(company_id), str(team_id), str(user_id))
        return self.delete(url, {})

    def update_batch_tasks(self, company_id, csv_data):
        """
        Batch update tasks using csv file contents.
        This process actually deletes the corresponding tasks and replaces 
        them with the newly specified details

        Parameters
          company_id    Company ID
          csv_data      Contents of the csv file
        """
        url = 'tasks/companies/%s/tasks/batch:%s' % (str(company_id), csv_data)
        return self.put(url, {})


class Finance(Namespace):
    api_url = 'finance/'
    version = 1

    def get_withdrawal_methods(self):
        """
        Retrieve a list of withdrawl available
        """
        return self.get('withdrawals')

    def post_withdrawal(self, method_ref, amount):
        """
        Post a withdrawl request

        Parameters
          method_ref    Withdrawl method reference
          Amount        Amount of withdrawl
        """
        url = 'withdrawals/%s' % method_ref
        data = {'amount': amount}
        return self.post(url, data)


class Ticket(Namespace):
    api_url = 'tickets/'
    version = 1
    
    def get_topics(self):
        """
        Retrieve ticket topics
        """
        url = 'topics'
        result = self.get(url)
        return result['topics']
    
    def get_ticket(self, ticket_key):
        """
        Retrieve details of a specific ticket

        Parameters
          ticket_key    Ticket key
        """
        url = 'tickets/%s' % str(ticket_key)
        result = self.get(url)
        return result['ticket']       

    def post_new_ticket(self, message, topic_id='', topic_api_ref='',
                        email='', name=''):
        """
        Post a new ticket

        Parameters
          message
          topic_id
          topic_api_ref
          email
          name
        """
        url = 'tickets'
        data = {'message': message,
                'topic_id': topic_id,
                'topic_api_ref': topic_api_ref,
                'email': email,
                }
        result = self.post(url, data)
        return result#TBD

    def post_reply_ticket(self, ticket_key, message):
        """
        Post reply to a specific ticket

        Parameters
          ticket_key    Ticket key
          message
        """
        url = 'tickets/%s' % str(ticket_key)
        data = {'message': message,}
        result = self.post(url, data)
        return result#TBD
       
class Url(Namespace):
    api_url = 'shorturl/'
    version = 1   
    
    def get_shorten(self, long_url):
        url = 'shorten'
        data = {'url': long_url}    
        result = self.get(url, data=data)
        return result['short_url']             

    def get_expand(self, short_url):
        url = 'expand'
        data = {'url': short_url}    
        result = self.get(url, data=data)
        return result['long_url']          
        
        
class GdsNamespace(Namespace):
    base_url = 'https://www.odesk.com/gds/'

    def urlopen(self, url, data={}, method='GET'):
        data = data.copy()
        query = self.client.urlencode(data)
        if method == 'GET':
            url += '?' + query
            request = HttpRequest(url=url, data=None, method=method)
            return urllib2.urlopen(request)
        return None

    def read(self, url, data={}, method='GET'):
        """
        Returns parsed Python object or raises an error
        """
        try:
            response = self.urlopen(url, data, method)
        except urllib2.HTTPError, e:
            raise_http_error(e)

        result = json.loads(response.read())
        return result

    def get(self, url, data={}):
        return self.read(self.full_url(url), data, method='GET')


class TimeReports(GdsNamespace):
    api_url = 'timereports/'
    version = 1

    def get_provider_report(self, provider_id, query, hours=False):
        '''
        Get caller's specific time report
        The caller of this API must be the provider himself

        Parameters
          provider_id   The provider_id of the caller
          query         The GDS query string
          hours         Limits the query to hour specific elements and hides all 
                        financial details (optional: defaults to False)
        '''
        url = 'providers/%s' % str(provider_id)
        if hours:
            url += '/hours'
        tq = str(query)
        result = self.get(url, data={'tq': tq})
        return result

    def get_company_report(self, company_id, query, hours=False):
        """
        Generate company wide time reports. All reporting fields available except
        earnings related fields. In order to access this API the authorized 
        user needs either hiring or finance permissions to all teams within 
        the company

        Parameters
          company_id    Company ID
          query         The GDS query string
          hours         Limits the query to hour specific elements and hides all 
                        financial details (optional: defaults to False)
        """
        url = 'companies/%s' % str(company_id)
        if hours:
            url += '/hours'
        tq = str(query)
        result = self.get(url, data={'tq': tq})
        return result

    def get_team_report(self, company_id, team_id, query, hours=False):
        """
        Generate team specific time reports.

        Parameters
          company_id    The Company ID
          team_id       The Team ID
          query         The GDS query string
          hours         Limits the query to hour specific elements and hides all 
                        financial details (optional: defaults to False)
        """
        url = 'companies/%s/teams/%s' % (str(company_id), str(team_id))
        if hours:
            url += '/hours'
        tq = str(query)
        result = self.get(url, data={'tq': tq})
        return result

    def get_agency_report(self, company_id, agency_id, query, hours=False):
        """
        Generate agency specific time reports.

        Parameters
          company_id    The Company ID
          agency_id     The Agency ID
          query         The GDS query string
          hours         Limits the query to hour specific elements and hides all 
                        financial details (optional: defaults to False)
        """
        url = 'companies/%s/agencies/%s' % (str(company_id), str(agency_id))
        if hours:
            url += '/hours'
        tq = str(query)
        result = self.get(url, data={'tq': tq})
        return result

class Finreports(GdsNamespace):
    api_url = 'finreports/'
    version = 2

    def get_provider_billings(self, provider_id, query):
        """
        Generate Billing Reports for a Specific Provider

        Parameters
          provider_id   Provider ID
          query         The GDS query string
        """
        url = 'providers/%s/billings' % str(provider_id)
        tq = str(query)
        result = self.get(url, data={'tq': tq})
        return result

    def get_provider_teams_billings(self, provider_team_id, query):
        """
        Generate Billing Reports for a Specific Provider's Team
        The authenticated user must be an admin or a staffing manager of the team

        Parameters
          provider_team_id  Provider's Team ID
          query             The GDS query string
        """
        url = 'provider_teams/%s/billings' % str(provider_team_id)
        tq = str(query)
        result = self.get(url, data={'tq': tq})
        return result

    def get_provider_companies_billings(self, provider_company_id, query):
        """
        Generate Billing Reports for a Specific Provider's Company
        The authenticated user must be the company owner

        Parameters
          provider_company_id   Provider's Company ID
          query                 The GDS query string
        """
        url = 'provider_companies/%s/billings' % str(provider_company_id)
        tq = str(query)
        result = self.get(url, data={'tq': tq})
        return result

    def get_provider_earnings(self, provider_id, query):
        """
        Generate Earning Reports for a Specific Provider

        Parameters
          provider_id   Provider ID
          query         The GDS query string
        """
        url = 'providers/%s/earnings' % str(provider_id)
        tq = str(query)
        result = self.get(url, data={'tq': tq})
        return result

    def get_provider_teams_earnings(self, provider_team_id, query):
        """
        Generate Earning Reports for a Specific Provider's Team

        Parameters
          provider_team_id  Provider's Team ID
          query             The GDS query string
        """
        url = 'provider_teams/%s/earnings' % str(provider_team_id)
        tq = str(query)
        result = self.get(url, data={'tq': tq})
        return result

    def get_provider_companies_earnings(self, provider_company_id, query):
        """
        Generate Earning Reports for a Specific Provider's Company

        Parameters
          provider_company_id   Provider's Team ID
          query                 The GDS query string
        """
        url = 'provider_companies/%s/earnings' % str(provider_company_id)
        tq = str(query)
        result = self.get(url, data={'tq': tq})
        return result

    def get_buyer_teams_billings(self, buyer_team_id, query):
        """
        Generate Billing Reports for a Specific Buyer's Team
        The authenticated user must be an admin or a staffing manager of the team

        Parameters
          buyer_team_id     Buyers's Team ID
          query             The GDS query string
        """
        url = 'buyer_teams/%s/billings' % str(buyer_team_id)
        tq = str(query)
        result = self.get(url, data={'tq': tq})
        return result

    def get_buyer_companies_billings(self, buyer_company_id, query):
        """
        Generate Billing Reports for a Specific Buyer's Company
        The authenticated user must be the company owner

        Parameters
          buyer_company_id  Buyer's Company ID
          query             The GDS query string
        """
        url = 'buyer_companies/%s/billings' % str(buyer_company_id)
        tq = str(query)
        result = self.get(url, data={'tq': tq})
        return result

    def get_buyer_teams_earnings(self, buyer_team_id, query):
        """
        Generate Earning Reports for a Specific Buyer's Team

        Parameters
          buyer_team_id     Buyer's Team ID
          query             The GDS query string
        """
        url = 'buyer_teams/%s/earnings' % str(buyer_team_id)
        tq = str(query)
        result = self.get(url, data={'tq': tq})
        return result

    def get_buyer_companies_earnings(self, buyer_company_id, query):
        """
        Generate Earning Reports for a Specific Buyer's Company

        Parameters
          buyer_company_id  Buyer's Team ID
          query             The GDS query string
        """
        url = 'buyer_companies/%s/earnings' % str(buyer_company_id)
        tq = str(query)
        result = self.get(url, data={'tq': tq})
        return result

    def get_financial_entities(self, accounting_id, query):
        """
        Generate Financial Reports for a Specific Account

        Parameters
          accounting_id     ID of an Accounting entity
          query             The GDS query string
        """
        url = 'financial_accounts/%s' % str(accounting_id)
        tq = str(query)
        result = self.get(url, data={'tq': tq})
        return result
    
    def get_financial_entities_provider(self, provider_id, query):
        """
        Generate Financial Reports for an owned Account

        Parameters
          provider_id   Provider ID
          query             The GDS query string
        """
        url = 'financial_account_owner/%s' % str(provider_id)
        tq = str(query)
        result = self.get(url, data={'tq': tq})
        return result


class NonauthGdsNamespace(GdsNamespace):
    '''
    This class does not add authentication parameters
    to request urls (api_sig, api_key & api_token)
    Some APIs return error if called with authentication parameters
    '''
    def urlopen(self, url, data={}, method='GET'):
        if method == 'GET':
            request = HttpRequest(url=url, data=data.copy(), method=method)
            return urllib2.urlopen(request)
        return None


class OConomy(NonauthGdsNamespace):
    '''
    oConomy Reports API
    '''
    api_url = 'oconomy/'
    version = 1

    def get_monthly_summary(self, month):
        '''get_monthly_summary(month)

        Monthly oDesk job market report

        Paramters
          month     'YYYYMM' or a datetime.date object
        '''
        if isinstance(month, date):
            month = '%04d%02d' % (date.year, date.month)
        else:
            month = str(month)
            _month_fmt = 'YYYYMM'
            if not len(month) == len(_month_fmt):
                raise ValueError('Format of month parameter (%s) should be %s' % (month, _month_fmt))
        url = 'summary/%s' % month
        result = self.get(url)
        return result

    def get_hours_worked_by_locations(self):
        '''get_hours_worked_by_locations

        Hours worked by location report
        '''
        url = 'hours_worked_by_locations'
        result = self.get(url)
        return result

    def get_hours_worked_by_weeks(self):
        '''get_hours_worked_by_weeks()

        oConomy weekly growth report
        '''
        url = 'hours_worked_by_weeks'
        result = self.get(url)
        return result

    def get_top_countries_by_hours(self):
        '''get_top_countries_by_hours()

        Top countries by hours worked for last 30 days report
        '''
        url = 'top_countries_by_hours'
        result = self.get(url)
        return result

    def get_earnings_by_categories(self):
        '''get_earnings_by_categories()

        Earnings by category report
        '''
        url = 'charges_by_categories'
        result = self.get(url)
        return result

    def get_most_requested_skills(self):
        '''get_most_requested_skills()

        Monthly most requested skills report
        '''
        url = 'most_requested_skills'
        result = self.get(url)
        return result


if __name__ == "__main__":
    import doctest
    doctest.testmod()
