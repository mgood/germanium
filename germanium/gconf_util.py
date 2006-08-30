# -*- coding: utf-8 -*-
#
# Copyright 2006 Matt Good <matt@matt-good.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

import os.path

import gconf
import gtk

class gconf_property(object):
    def __init__(self, key, type=gconf.VALUE_STRING):
        self.client = gconf.client_get_default()
        self.key = key
        self.type = type
        self.value = _from_gconf(self.client.get(key))
        self.client.notify_add(self.key, self._gconf_callback)

    def __get__(self, inst, cls):
        if inst is None:
            return self
        return self.value

    def __set__(self, inst, value):
        self.client.set(self.key, _to_gconf(self.type, value))

    def _gconf_callback(self, client, cnx_id, entry, data):
        self.value = _from_gconf(entry.value)


def bind_file_chooser(chooser, key):
    def getter(chooser):
        return chooser.get_current_folder_uri()
    def setter(chooser, value):
        if value is None:
            chooser.set_current_folder(os.path.expanduser('~'))
        elif chooser.get_current_folder_uri() != value:
            chooser.set_current_folder_uri(value)
    bind_gconf(chooser, key, getter, setter, 'current_folder_changed')

def bind_combo_box(combo_box, key, options):
    model = gtk.ListStore(str, str)
    for lbl, value in options:
        model.append([lbl, value])
    combo_box.set_model(model)

    def getter(combo_box):
        return options[combo_box.get_active()][1]
    def setter(combo_box, new_value):
        for idx, (_, value) in enumerate(options):
            if value == new_value:
                combo_box.set_active(idx)
                break
        else:
            combo_box.set_active(0)
            client = gconf.client_get_default()
            client.set_string(key, options[0][1])
    bind_gconf(combo_box, key, getter, setter)

def bind_checkbox(checkbox, key):
    def getter(checkbox):
        return checkbox.get_active()
    def setter(checkbox, value):
        checkbox.set_active(bool(value))
    bind_gconf(checkbox, key, getter, setter, 'toggled', gconf.VALUE_BOOL)

def bind_gconf(widget, key, getter, setter, signal='changed',
               type=gconf.VALUE_STRING):
    client = gconf.client_get_default()
    setter(widget, _from_gconf(client.get(key)))
    client.notify_add(key, _gconf_changed, (widget, setter))
    widget.connect(signal, _gui_changed, (key, type, getter))

def _to_gconf(type, value):
    gconf_value = gconf.Value(type)
    if type == gconf.VALUE_STRING:
        gconf_value.set_string(value)
    elif type == gconf.VALUE_BOOL:
        gconf_value.set_bool(value)
    elif type == gconf.VALUE_INT:
        gconf_value.set_int(value)
    return gconf_value

def _from_gconf(value):
    if value is None:
        return None
    elif value.type == gconf.VALUE_STRING:
        return value.get_string()
    elif value.type == gconf.VALUE_BOOL:
        return value.get_bool()
    elif value.type == gconf.VALUE_INT:
        return value.get_int()

def _gconf_changed(client, cnx_id, entry, (widget, setter)):
    setter(widget, _from_gconf(entry.value))

def _gui_changed(widget, (key, type, getter)):
    value = getter(widget)
    gconf.client_get_default().set(key, _to_gconf(type, value))


