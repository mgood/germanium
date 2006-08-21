# -*- coding: utf-8 -*-

__all__ = ["Task", "Factory", "GObjectSingletonMeta"]

import gobject
import dbus, dbus.glib
from xml.dom import minidom

MATHUSALEM_SERVICE = 'org.gnome.Mathusalem'

MATHUSALEM_FACTORY_PATH = '/org/gnome/Mathusalem'
MATHUSALEM_TASKLIST_PATH = '/org/gnome/Mathusalem/Tasks'

MATHUSALEM_FACTORY_IFACE = 'org.gnome.Mathusalem'
MATHUSALEM_TASK_IFACE = 'org.gnome.Mathusalem.Task'

class Task(gobject.GObject):
    """Mathusalem Task D-Bus object proxy"""

    __gsignals__ = {
        'started'         : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, tuple()),
        'paused'          : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, tuple()),
        'completed'       : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, tuple()),
        'aborted'         : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, tuple()),
        'progress-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_UINT, )),
    }

    def __init__(self, object_path):
        """Create a proxy to the given Task D-Bus object"""

        gobject.GObject.__init__(self)
        bus = dbus.SessionBus()
        obj = bus.get_object(MATHUSALEM_SERVICE, object_path)
        task_iface = dbus.Interface(obj, MATHUSALEM_TASK_IFACE)

        # Init proxies (should probably be lazy)
        self.interfaces = { MATHUSALEM_TASK_IFACE: task_iface }
        for iface in task_iface.ListInterfaces():
            if not self.interfaces.has_key(iface):
                self.interfaces[iface] = dbus.Interface(obj, iface)

        # Init properties
        self.path = object_path
        self._props = dict()

        # Proxy signals coming from the bus
        task_iface.connect_to_signal('StatusChanged',
                                     self.on_status_changed)
        task_iface.connect_to_signal('ProgressChanged',
                                     self.on_progress_changed)

    def __repr__(self):
        return "<%s.Task '%s' at %x>" % (__name__, self.path, id(self))

    def __getitem__(self, y):
        if '.' in y:
            return self.interfaces[y]
        for key in self.interfaces.iterkeys():
            if y == key[key.rindex('.')+1:]:
                return self.interfaces[key]
        raise KeyError(y)

    # Signals
    def on_status_changed(self, status):
        signals = ('started', 'paused', 'aborted', 'completed')
        self.emit(signals[status-1])
    
    def on_progress_changed(self, progress):
        self.emit('progress-changed', progress)
    
    def do_started(self):
        self._props['status'] = 'started'

    def do_paused(self):
        self._props['status'] = 'paused'

    def do_completed(self):
        self._props['status'] = 'completed'
        self._props['progress'] = 100

    def do_aborted(self):
        self._props['status'] = 'aborted'

    def do_progress_changed(self, progress):
        self._props['progress'] = progress       

    # Properties
    def get_title(self):
        if 'title' not in self._props:
            self._props['title'] = self.interfaces[MATHUSALEM_TASK_IFACE].GetTitle()
        return self._props['title']

    def get_owner(self):
        if 'owner' not in self._props:
            self._props['owner'] = self.interfaces[MATHUSALEM_TASK_IFACE].GetOwner()
        return self._props['owner']

    def get_progress(self):
        if 'progress' not in self._props:
            self._props['progress'] = self.interfaces[MATHUSALEM_TASK_IFACE].GetProgress()
        return self._props['progress']

    def set_progress(self, progress):
        if self._props['status'] not in ('completed', 'aborted'):
            self._props['progress'] = progress
            self.interfaces[MATHUSALEM_TASK_IFACE].SetProgress(dbus.UInt32(progress))

    def get_status(self):
        if 'status' not in self._props:
            self._props['status'] = self.interfaces[MATHUSALEM_TASK_IFACE].GetStatus()
        return self._props['status']

    title = property(get_title)
    owner = property(get_owner)
    progress = property(get_progress, set_progress)
    status = property(get_status)

    # Methods
    def start(self):
        self.interfaces[MATHUSALEM_TASK_IFACE].Start()

    def pause(self):
        self.interfaces[MATHUSALEM_TASK_IFACE].Pause()

    def abort(self):
        self.interfaces[MATHUSALEM_TASK_IFACE].Abort()

class GObjectSingletonMeta(gobject.GObjectMeta):
    """GObject Singleton Metaclass"""

    def __init__(klass, name, bases, dict):
        gobject.GObjectMeta.__init__(klass, name, bases, dict)
        klass.__instance = None

    def __call__(klass, *args, **kwargs):
        if klass.__instance is None:
            klass.__instance = gobject.GObjectMeta.__call__(klass, *args, **kwargs)
        return klass.__instance

class Factory(gobject.GObject):
    """Mathusalem D-Bus object proxy"""

    __metaclass__ = GObjectSingletonMeta

    __gsignals__ = {
        'task-registered': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_OBJECT, )),
    }

    def __init__(self):
        gobject.GObject.__init__(self)
        self._bus = dbus.SessionBus()
        obj = self._bus.get_object(MATHUSALEM_SERVICE, MATHUSALEM_FACTORY_PATH)
        self._proxy = dbus.Interface(obj, MATHUSALEM_FACTORY_IFACE)
        self._proxy.connect_to_signal('TaskRegistered', self.task_registered)

    def __repr__(self):
        return "<%s.Factory at %x>" % (__name__, id(self))

    # Signals
    def task_registered(self, object_path):
        task = Task(object_path)
        self.emit("task-registered", task)

    # Properties
    def get_version(self):
        return tuple(self._proxy.GetVersion())

    version = property(get_version)

    # Methods
    def register_task(self, ifaces, title, owner):
        return self._proxy.RegisterTask(ifaces, title, owner)

    def get_registered_tasks(self):
        obj = self._bus.get_object(MATHUSALEM_SERVICE, MATHUSALEM_TASKLIST_PATH)
        tasklist = dbus.Interface(obj, 'org.freedesktop.DBus.Introspectable')

        tree = minidom.parseString(tasklist.Introspect())
        tree = tree.childNodes[1] # skip doctype, take root node
        return [Task(MATHUSALEM_TASKLIST_PATH + '/' + node.getAttribute('name'))
                    for node in tree.childNodes
                    if node.__class__ == minidom.Element and tree.tagName == 'node']

gobject.type_register(Factory)
gobject.type_register(Task)

# ex:ts=4:et:
