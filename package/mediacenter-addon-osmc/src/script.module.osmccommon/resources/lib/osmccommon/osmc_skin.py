# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC

    This file is part of script.module.osmccommon

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    Skin support for the MyOSMC windows.

    Window files
        Every MyOSMC window is named script-myosmc*.xml. Kodi looks for that
        name in the active skin first, so a skin restyles a window by shipping
        its own copy in its xml folder. Otherwise the add-on's own Default copy
        is used.

        The add-on's copies use the osmc_addon_* fonts that ubiquifonts adds
        to the skin. Skin fonts are sized in the skin's own resolution, so for
        720p skins the build makes a twin of each file, script-myosmc*-720.xml,
        that uses the smaller osmc_addon_720_* fonts.

    Colours
        The add-on's copies take their colours from these Home window
        properties, set by apply_theme() before any MyOSMC window opens:

            MyOSMC.Color.Background  Text  TextDim  TextBright  Focus
                         Selected  Active  Disabled  Shadow

        A skin changes them by setting MyOSMC.Skin.Color.<role> on the Home
        window, e.g. in Startup.xml or Home.xml:

            SetProperty(MyOSMC.Skin.Color.Focus,button_focus,home)

        The value can be an aarrggbb colour or the name of one of the skin's
        own colours. Roles the skin leaves empty keep the OSMC default.

    First-boot walkthrough
        The walkthrough runs before the user has chosen a skin, so windows it
        opens (the network settings) keep OSMC's original look: the OSMC
        default colours, and the add-on's own window file even if the skin has
        a copy. The service sets the Home property walkthrough_is_running while
        the walkthrough is open.

        Kodi always looks for a window file in the active skin first, so to
        get past a skin's copy the build makes an alias that no skin ships,
        script-myosmc*-default.xml, for each window the walkthrough can open.
"""

import os
import xml.etree.ElementTree as ElementTree

import xbmc
import xbmcgui
import xbmcvfs

HOME_WINDOW = 10000

# set by service.osmc.settings while the first-boot walkthrough is open
WALKTHROUGH_PROPERTY = 'walkthrough_is_running'

THEME_DEFAULTS = {
    'Background': 'ff0b2430',
    'Text': '66ffffff',
    'TextDim': 'ff808080',
    'TextBright': 'fff1f1f1',
    'Focus': 'ffe0b074',
    'Selected': 'ffffffff',
    'Active': 'ff8ff5ee',
    'Disabled': 'ff000000',
    'Shadow': '44000000',
}

_SKIN_INFO = {}


def apply_theme(skinned=True):
    """ Publish the colours the MyOSMC windows use. An empty colour would
        draw nothing at all, so every role always gets a value.

        skinned  False publishes the OSMC defaults and ignores the skin's
                 colours; the next skinned call puts the skin's back """
    home = xbmcgui.Window(HOME_WINDOW)
    for role, default in THEME_DEFAULTS.items():
        value = (skinned and home.getProperty('MyOSMC.Skin.Color.%s' % role)) or default
        if home.getProperty('MyOSMC.Color.%s' % role) != value:
            home.setProperty('MyOSMC.Color.%s' % role, value)


def _skin_info():
    """ (xml folder, height) of the active skin, read from its addon.xml """
    skin_id = xbmc.getSkinDir()
    if skin_id in _SKIN_INFO:
        return _SKIN_INFO[skin_id]

    folder = None
    height = None
    try:
        root = ElementTree.parse(xbmcvfs.translatePath('special://skin/addon.xml')).getroot()
        resolutions = root.findall('.//res')
        default = [res for res in resolutions if res.get('default') == 'true']
        res = (default or resolutions)[0]
        folder = res.get('folder')
        height = int(res.get('height'))
    except (OSError, ElementTree.ParseError, IndexError, TypeError, ValueError):
        pass

    if not height:
        # set by ubiquifonts from the skin's folder layout
        try:
            height = int(xbmcgui.Window(HOME_WINDOW).getProperty('SkinHeight'))
        except ValueError:
            height = 1080

    _SKIN_INFO[skin_id] = (folder, height)
    return folder, height


def in_walkthrough():
    """ True while the first-boot walkthrough is open """
    return bool(xbmcgui.Window(HOME_WINDOW).getProperty(WALKTHROUGH_PROPERTY))


def _addon_has(script_path, filename):
    return os.path.isfile(os.path.join(script_path, 'resources', 'skins', 'Default', '1080i', filename))


def window_xml(name, script_path):
    """ The xml file name to open a MyOSMC window with.

        name         the window's file, e.g. 'script-myosmc-network.xml'
        script_path  the path of the add-on that ships the Default copy
    """
    skinned = not in_walkthrough()
    apply_theme(skinned=skinned)

    folder, height = _skin_info()
    base = name

    if skinned:
        # the skin has its own copy: Kodi will use it, whatever its resolution
        if folder:
            skin_copy = xbmcvfs.translatePath('special://skin/%s/%s' % (folder, name))
            if os.path.isfile(skin_copy):
                return name

    else:
        # the original look: ask for the alias no skin ships, when the build
        # made one (a copy of src without building has none, and a skin copy
        # of the window would then still win)
        alias = name[:-len('.xml')] + '-default.xml'
        if _addon_has(script_path, alias):
            base = alias

    # a 720p skin gets the twin with the smaller fonts, when the build made one
    if height < 1080:
        twin = base[:-len('.xml')] + '-720.xml'
        if _addon_has(script_path, twin):
            return twin

    return base
