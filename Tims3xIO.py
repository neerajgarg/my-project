#!/usr/bin/env python

# $Id: Tims3xIO.py,v 1.4 2005/03/01 20:04:57 tombry Exp $

import getpass, httplib, mimetypes, os, re, string, sys, traceback, urllib

sys.path.append('/autons/tims/lib/python')

import socket


class Tims3xIO:
    """
    A python module for interacting with the TIMS 3.6 (and later) API.

    To use this code in client software, import this file and then do
    something akin to:

    from Tims3xIO import *

    obj = Tims3xIO(USERNAME='klassa')

    token = obj.get_token(TNUM=MY_PROJECT_TNUM)

    xml = something_that_generates_xml(token)

    try:
        msg = obj.send(BASE=url, PATH=path, METHOD='POST', XML=xml)
        print "POST returned", msg

        msg = obj.send(BASE=url, PATH=path, METHOD='GET')
        print "GET returned", msg

        msg = obj.POST(BASE=url, PATH=path, XML=xml)
        print "GET returned", msg

    except:
        print "There was a problem getting to TIMS:", sys.exc_info()[0]
        raise
    """

    def __init__ (self, **dict):
        """
        Constructor.

        The dictionary is optional.  If present, may contain the
        following keys (which are both optional):

        USERNAME

        The username of the person on whose behalf the import is taking
        place (so that the appropriate automation token can be found).
        For example, if your username is "jsmith" but the intent is for
        TIMS 3.x to think that "mdoe" did the work, you would pass
        "mdoe", without the quotes, here (and then also pass mdoe's
        token data in the TOKEN field, or have mdoe's token data
        available in your own ~/.tims directory).

        TOKEN

        Either the target user's automation token for the project with
        which you intend to interact, or a formatted string that
        contains the target user's token for each database with which
        you may wish to interact.  Using the "mdoe" example again, if
        mdoe's token for the "x" database is "01234", and for the "y"
        database is "98765", you would pass "x=01234,y=98765" (without
        the quotes) here.

        If you pass a single TOKEN explicitly, get_token() will only
        ever return the value you provide (i.e. no database-specific
        match is sought.

        If the USERNAME key is omitted, the username that owns the
        process is used by default.

        If the TOKEN key is omitted, the data is retrieved from the
        ".tims" directory in the home directory of the owning process
        (where it should be stored according to the instructions given
        by the TIMS application, when an automation token is requested).
        """

        self.USERNAME = "shuchugh"
        self.TOKEN = "090062203D5018003778014400140000"
        self.TOKENMAP = {}

        if dict.has_key('USERNAME'): self.USERNAME = dict['USERNAME']
        if dict.has_key('TOKEN'): self.TOKEN = dict['TOKEN']

        if self.USERNAME == '': self.USERNAME = getpass.getuser()

        f_regex = re.compile('^api-token-([^-]+)-([^-]+)\.txt$')
        t_regex = re.compile('^\s*([^=]+)\s*=\s*([^=]+)\s*$')

        if self.TOKEN == '':
            tokens = []
            dottims = os.path.expanduser('~/.tims')
            for file in os.listdir(dottims):
                match = f_regex.search(file)
                if not match: continue
                (db, uname) = (match.group(1), match.group(2))
                if uname != self.USERNAME: continue
                t = None
                try:
                    fh = open(os.path.join(dottims, file), 'r')
                except:
                    continue
                try:
                    t = fh.read()
                finally:
                    fh.close()
                if t == None: continue
                tokens.append(string.lower(db) + '=' + string.strip(t))
            self.TOKEN = string.join(tokens, ',')

        if string.find(self.TOKEN, '=') != -1:
            for t in string.split(self.TOKEN, ','):
                match = t_regex.search(t)
                if not match:
                    raise 'ERROR: Badly-formatted token data.'
                (d, t) = (match.group(1), match.group(2))
                self.TOKENMAP[string.lower(d)] = t
            self.TOKEN = ''

    def get_token (self, **dict):
        """
        Returns the automation token for the project with TIMS 3.x ID
        TNUM, for the username supplied to the constructor.

        The dictionary should contain just one key:

        TNUM

        The tracking number of the project of interest.
        """

        if not dict.has_key('TNUM'): raise('ERROR: TNUM is required.')

        if self.TOKEN != '': return self.TOKEN

        regex = re.compile('^T([bcdfghjklmnpqrstvwxyz]+)\d+p$')

        match = regex.search(dict['TNUM'])

        if match:
            db = string.lower(match.group(1))
            if self.TOKENMAP.has_key(db):
                return self.TOKENMAP.get(db)

        raise('ERROR: No token for project ' + dict['TNUM'] + '.')

    def send (self, **dict):
        """
        Sends data to TIMS 3.x.

        The dictionary is required, and should contain the following
        keys (except XML, which is optional for a GET operation):

        BASE

        The base URL for the destination.  For example,
        "http://tims.cisco.com".

        PATH

        The rest of the URL.  This value is tacked onto BASE, to form
        the complete URL.  For example, "xml/Tx11c/entity.svc".

        METHOD

        The HTTP method to use.  Should be either "GET" or "POST".

        XML

        The actual XML message to send, as a string.  Ignored for a GET.
        """

        base   = 'http://tims.cisco.com'
        path   = ''
        method = ''
        xml    = ''

        if dict.has_key('BASE'):   base   = dict['BASE']
        if dict.has_key('PATH'):   path   = dict['PATH']
        if dict.has_key('METHOD'): method = dict['METHOD']
        if dict.has_key('XML'):    xml    = dict['XML']

        if path   == '': raise('ERROR: PATH is required.')
        if method == '': raise('ERROR: METHOD is required.')

        if method == 'POST' and xml == '':
            raise('ERROR: XML is required for a POST operation.')

        if string.find(base, 'http://') == 0:
            base = base[7:]

        while string.find(path, '/') == 0:
            path = path[1:]
        s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(60)

        try:
            if method == 'GET':
                return urllib.urlopen('http://' + base + '/' + path).read()
            elif method == 'POST':
                return _post_multipart(
                    base, 'http://' + base + '/' + path, [],
                    [['xmldata', 'xmldata', xml]])
            else:
                raise('ERROR: Invalid method.')
        except IOError:
            raise('ERROR: The database is down ' +
                  '(or an invalid host was specified).')
        except socket.timeout:
            raise('ERROR: The database is down ' +
                  '(or an invalid host was specified).')

    def GET (self, **dict):
        """
        Shortcut for doing a GET.
        """

        dict['METHOD'] = 'GET'

        return apply(self.send, (), dict)

    def POST (self, **dict):
        """
        Shortcut for doing a POST.
        """

        dict['METHOD'] = 'POST'

        return apply(self.send, (), dict)


##########################################################################
# The following chunk of code taken from the Python Cookbook hosted
# at ActiveState.COM.  The original author is Wade Leftwich.  Used
# without permission (though I don't know that permission is needed).
#
# START
##########################################################################

def _post_multipart (host, selector, fields, files):
    """
    Post fields and files to an http host as multipart/form-data.
    fields is a sequence of (name, value) elements for regular form
    fields.  files is a sequence of (name, filename, value) elements
    for data to be uploaded as files.  Return the server's response
    page.
    """
    content_type, body = _encode_multipart_formdata(fields, files)

    h = httplib.HTTP(host)

    h.putrequest('POST', selector)
    h.putheader('content-type', content_type)
    h.putheader('content-length', str(len(body)))
    h.endheaders()

    h.send(body)

    errcode, errmsg, headers = h.getreply()

    if errcode != 200:
        raise("ERROR: The database is down (or an invalid host was " +
              "specified).")

    return h.file.read()

def _encode_multipart_formdata (fields, files):
    """
    Fields is a sequence of (name, value) elements for regular form
    fields.  files is a sequence of (name, filename, value) elements
    for data to be uploaded as files.  Return (content_type, body)
    ready for httplib.HTTP instance.
    """

    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []

    for (key, value) in fields:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)

    for (key, filename, value) in files:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' %
                 (key, filename))
        L.append('Content-Type: %s' % _get_content_type(filename))
        L.append('')
        L.append(value)

        L.append('--' + BOUNDARY + '--')
        L.append('')

    body = CRLF.join(L)

    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY

    return content_type, body

def _get_content_type (filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

##########################################################################
# END
#
# (of Python Cookbook code)
##########################################################################


def test ():

    xml = """
<Tims xmlns="http://tims.cisco.com/namespace"
      xmlns:xlink="http://www.w3.org/1999/xlink"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="http://tims.cisco.com/namespace
                          http://tims.cisco.com/xsd/Tims.xsd"
      msgID="SoMeThInG-RaNdOm-1085410010">
    <Credential user="klassa" token="3B0C7C2G530039001800000000001000" />
    <Search scope="folder" entity="folder" root="Th705652f"
            casesensitive="true" save="false">
        <Title>Bogus Because JK is a L@m3r</Title>
        <TextCriterion operator="is">
            <FieldName>Title</FieldName>
            <Value>Imports</Value>
        </TextCriterion>
    </Search>
</Tims>
"""

    print "\nTest", 1, "\n"

    try:
        obj = Tims3xIO()
        print "Username is:", obj.USERNAME
    except:
        print "Problem:", sys.exc_info()[0]
        traceback.print_tb(sys.exc_info()[2])

    print "\nTest", 2, "\n"

    try:
        obj = Tims3xIO(USERNAME='fred')
        print "Token for fred is:", obj.get_token(TNUM='Tx123p')
    except:
        print "(Expected) Problem:", sys.exc_info()[0]

    print "\nTest", 3, "\n"

    try:
        obj = Tims3xIO(USERNAME='fred', TOKEN='12345')
        print "Token for fred (fixed) is:", obj.get_token(TNUM='Tx123p')
    except:
        print "Problem:", sys.exc_info()[0]
        traceback.print_tb(sys.exc_info()[2])

    print "\nTest", 4, "\n"

    try:
        obj = Tims3xIO()
        print "Token (user) for Tl123p is:", obj.get_token(TNUM='Tl123p')
    except:
        print "Problem:", sys.exc_info()[0]
        traceback.print_tb(sys.exc_info()[2])

    print "\nTest", 5, "\n"

    try:
        obj = Tims3xIO()
        print obj.POST(BASE='rusty', PATH='xml/Th2501p/search.svc', XML=xml)
    except:
        print "Problem:", sys.exc_info()[0]
        traceback.print_tb(sys.exc_info()[2])

    print "\nTest", 6, "\n"

    try:
        obj = Tims3xIO()
        print obj.GET(BASE='rusty', PATH='xml/Th733278f/entity.svc')
    except:
        print "Problem:", sys.exc_info()[0]
        traceback.print_tb(sys.exc_info()[2])

    print "\nTest", 7, "\n"

    try:
        obj = Tims3xIO()
        print obj.send(BASE='rusty', PATH='xml/Th2501p/search.svc',
                       METHOD='POST', XML=xml)
    except:
        print "Problem:", sys.exc_info()[0]
        traceback.print_tb(sys.exc_info()[2])

    print "\nTest", 8, "\n"

    try:
        obj = Tims3xIO()
        print obj.send(BASE='rusty', PATH='xml/Th733278f/entity.svc',
                       METHOD='GET')
    except:
        print "Problem:", sys.exc_info()[0]
        traceback.print_tb(sys.exc_info()[2])

    print "\nTest", 9, "\n"

    try:
        obj = Tims3xIO()
        print obj.GET(PATH='xml/Tl3029678r/twiddle-regex/file.svc')
    except:
        print "Problem:", sys.exc_info()[0]
        traceback.print_tb(sys.exc_info()[2])

if __name__ == '__main__':
    test()