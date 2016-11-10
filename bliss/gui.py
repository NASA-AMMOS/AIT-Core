# Copyright 2015 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""
BLISS GUI

The bliss.gui module provides the web-based (HTML5/CSS/Javascript)
BLISS Graphical User Interface (GUI).
"""

import collections
import copy
import json
import os
import webbrowser

import bottle
import gevent
import gevent.event
import gevent.monkey
import geventwebsocket
import requests

gevent.monkey.patch_all()

import bliss


if 'gui' in bliss.config and 'html_root' in bliss.config.gui:
    cfg_path = bliss.config.gui.html_root
    cfg_path = os.path.expanduser(cfg_path)

    if os.path.isabs(cfg_path):
        HTMLRoot = cfg_path
    else:
        HTMLRoot = os.path.join(bliss.config._ROOT_DIR, cfg_path)

    HTMLRoot = os.path.normpath(HTMLRoot)
else:
    HTMLRoot = os.path.join(bliss.config._ROOT_DIR, 'gui')

App      = bottle.Bottle()

bottle.debug(True)
bottle.TEMPLATE_PATH.append(HTMLRoot)

class Deque (object):
    """Deque

    A Python collections.deque that can be used in a Gevent context.
    Get operations will block until an item is available in the Deque.
    """

    def __init__ (self, maxlen=None, deque=None):
        """Creates a new Deque, optionally cloned from the existing deque.

        If maxlen is not specified or is None, deques may grow to an
        arbitrary length.  Otherwise, the deque is bounded to the
        specified maximum length.  Once a bounded length deque is full,
        when new items are added, a corresponding number of items are
        discarded from the opposite end.
        """
        if deque is None:
            self.deque = collections.deque(maxlen=maxlen)
        else:
            self.deque = copy.copy(deque)

        self.event = gevent.event.Event()

        if len(self.deque) > 0:
            self.event.set()

    def __copy__ (self):
        """Creates a new copy of this Deque (via Python copy.copy())."""
        return Deque(deque=self.deque)

    def __len__ (self):
        """The number of items in this Deque."""
        return len(self.deque)

    def get (self):
        """Removes and returns the oldest item inserted into this Deque.

        This method blocks if the Deque is empty.
        """
        self.event.wait()
        item = self.deque.popleft()

        if len(self.deque) is 0:
            self.event.clear()

        return item

    def put (self, item):
        """Adds item to this Deque.

        This method does not block.  Either the Deque grows to consume
        available memory, or if this Deque has a maxlen, the oldest
        inserted item is removed.
        """
        self.deque.append(item)
        self.event.set()


class Session (object):
    """Session

    A Session manages the state for a single GUI client connection.
    Sessions are managed through a SessionStore and may be used as a
    Python context.
    """

    def __init__ (self, store=None, prototype=None):
        """Creates a new Session, optionally cloned from the prototype
        Session."""
        if prototype is None:
            self.events    = Deque( maxlen=100     )
            self.messages  = Deque( maxlen=100     )
            self.telemetry = Deque( maxlen=30 * 60 )
        else:
            self.events    = copy.copy( prototype.events    )
            self.messages  = copy.copy( prototype.messages  )
            self.telemetry = copy.copy( prototype.telemetry )

        self._store          = store
        self._numConnections = 0

    def __copy__ (self):
        """Creates a new copy of this Session (via Python copy.copy())."""
        return Session(prototype=self)

    def __enter__ (self):
        """Begins a Session context / connection."""
        self._numConnections += 1
        return self

    def __exit__ (self, exc_type, exc_value, traceback):
        """Ends a Session context / connection.

        If no more active connections exist, the Session is deleted
        from its SessionStore.
        """
        assert self._numConnections > 0
        self._numConnections -= 1

        # FIXME: Age sessions out of existence instead?
        # if self._numConnections is 0 and self._store is not None:
        #     self._store.remove(self)

    @property
    def id (self):
        """A unique identifier for this Session."""
        return str( id(self) )


class SessionStore (dict):
    """SessionStore

    A SessionStore manages one or more Sessions.  SessionStores
    associate a Session with a GUI clients through an HTTP cookie.
    """
    Global = Session()

    def __init__ (self, *args, **kwargs):
        """Creates a new SessionStore."""
        dict.__init__(self, *args, **kwargs)

    def addTelemetry (self, packet):
        """Adds a telemetry packet to all Sessions in the store."""
        SessionStore.Global.telemetry.put(packet)
        for session in self.values():
            session.telemetry.put(packet)

    def addMessage (self, msg):
        """Adds a log message to all Sessions in the store."""
        SessionStore.Global.messages.put(msg)
        for session in self.values():
            session.messages.put(msg)

    def addEvent (self, name, data):
        """Adds an event to all Sessions in the store."""
        event = { 'name': name, 'data': data }
        SessionStore.Global.events.put(event)
        for session in self.values():
            session.events.put(event)

    def current (self):
        """Returns the current Session for this HTTP connection or raise an
        HTTP 401 Unauthorized error.
        """
        session = self.get( bottle.request.get_cookie('sid') )
        if session is None:
            raise bottle.HTTPError(401, 'Invalid Session Id')
        return session

    def create (self):
        """Creates and returns a new Session for this HTTP connection.

        New sessions inherit history from the SessionStore Global
        session.
        """
        session          = Session(self, SessionStore.Global)
        self[session.id] = session
        bottle.response.set_cookie('sid', session.id)
        return session

    def remove (self, session):
        """Removes the given Session from this SessionStore."""
        del self[session.id]


Sessions = SessionStore()

def getBrowserName (browser):
    return getattr(browser, 'name', getattr(browser, '_name', '(none)'))

def startBrowser (url, name=None):
    browser = None

    if name is not None and name.lower() == 'none':
        bliss.log.info('Will not start any browser since --browser=none')
        return

    try:
        browser = webbrowser.get(name)
    except webbrowser.Error:
        old     = name or 'default'
        msg     = 'Could not find browser: %s.  Will use: %s.'
        browser = webbrowser.get()
        bliss.log.warn(msg, name, getBrowserName(browser))

    if type(browser) is webbrowser.GenericBrowser:
        msg = 'Will not start text-based browser: %s.'
        bliss.log.info(msg % getBrowserName(browser))
    elif browser is not None:
        bliss.log.info('Starting browser: %s' % getBrowserName(browser))
        browser.open_new(url)

@App.route('/')
def handle ():
    Sessions.create()
    return bottle.template('index.html')

@App.route('/events', method='GET')
def handle ():
    """Endpoint that pushes Server-Sent Events to client"""
    with Sessions.current() as session:
        bottle.response.content_type  = 'text/event-stream'
        bottle.response.cache_control = 'no-cache'
        yield 'event: connected\ndata:\n\n'

        while True:
            event = session.events.get()
            bottle.response.content_type  = 'text/event-stream'
            bottle.response.cache_control = 'no-cache'
            yield 'data: %s\n\n' % json.dumps(event)

@App.route('/events', method='POST')
def handle ():
    with Sessions.current() as session:
        name = bottle.request.POST.name
        data = bottle.request.POST.data
        Sessions.addEvent(name, data)

@App.route('/<pathname:path>')
def handle (pathname):
    return bottle.static_file(pathname, root=HTMLRoot)

@App.route('/bsc/handlers', method='GET')
def handle():
    try:
        r = requests.get('http://{}:{}'.format(
            bliss.config._config['gui']['bsc_host'],
            bliss.config._config['gui']['bsc_port']))
        data = r.json()
    except requests.ConnectionError:
        data = {}

    capturers = []
    for address, handlers in data.iteritems():
        for handler in handlers:
            host, port = handler['address']
            if host == '':
                host = bliss.config._config['gui']['bsc_host'],
            capturers.append([
                handler['handler']['name'],
                handler['conn_type'],
                '{}:{}'.format(host, port)
            ])

    return {'capturers': capturers}

@App.route('/bsc/create', method='POST')
def handle():
    try:
        r = requests.post(
            'http://{}:{}/{}/start'.format(
                bliss.config._config['gui']['bsc_host'],
                bliss.config._config['gui']['bsc_port'],
                bottle.request.POST.name),
            data={
                'loc': bliss.config._config['gui']['bsc_handler_host'],
                'port': bliss.config._config['gui']['bsc_handler_port'],
                'conn_type': bliss.config._config['gui']['bsc_handler_conn_type'],
            }
        )

        bottle.response.status = r.status_code
    except requests.ConnectionError:
        bottle.response.status = 500

@App.route('/bsc/remove', method='POST')
def handle():
    try:
        r = requests.delete('http://{}:{}/{}/stop'.format(
                bliss.config._config['gui']['bsc_host'],
                bliss.config._config['gui']['bsc_port'],
                bottle.request.POST.name))

        bottle.response.status = r.status_code
    except requests.ConnectionError:
        bottle.response.status = 500
