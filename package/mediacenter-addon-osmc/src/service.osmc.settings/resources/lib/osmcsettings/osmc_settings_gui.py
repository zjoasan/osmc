# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of service.osmc.settings

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import os
import sys
import threading
import traceback
from io import open

import xbmc
import xbmcaddon
import xbmcgui
from osmccommon.osmc_language import LangRetriever
from osmccommon.osmc_logging import StandardLogger
from osmccommon.osmc_logging import clog
from osmccommon.osmc_skin import apply_theme
from osmccommon.osmc_skin import window_xml

ADDON_ID = 'service.osmc.settings'

# Created as root when the device's support ends; the second records, in
# osmc's home, that the message has been shown.
END_OF_LIFE_FLAG = '/end_of_life_message'
END_OF_LIFE_SHOWN = '/home/osmc/.end_of_life_message_shown'

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log


# The look of MyOSMC lives entirely in script-myosmc.xml. A skin can ship its
# own copy of that file to restyle it; this module only supplies the data and
# handles clicks. Keep these ids in step with the comment at the top of the xml.
XML_FILE = 'script-myosmc.xml'
CENTER_ID = 100       # closes MyOSMC (settings are applied on close)
SLOT_BASE_ID = 101    # module slot n is control SLOT_BASE_ID + n
ADVANCED_ID = 909     # Advanced Settings (beta)
LIST_ID = 9000        # optional container for skins that prefer a list


class OSMCGui(xbmcgui.WindowXMLDialog):

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, **kwargs):
        super(OSMCGui, self).__init__(xmlFilename=strXMLname,
                                      scriptPath=strFallbackPath,
                                      defaultSkin=strDefaultName)
        self.live_modules = kwargs.get('live_modules', [])

        self._addon = kwargs.get('addon')
        self.window = kwargs.get('window', xbmcgui.Window(10000))
        self._lang = None

        log('%d live modules' % len(self.live_modules))

        self.first_run = True

    @property
    def addon(self):
        if not self._addon:
            self._addon = xbmcaddon.Addon(ADDON_ID)
        return self._addon

    def lang(self, value):
        if not self._lang:
            retriever = LangRetriever(self.addon)
            self._lang = retriever.lang
        return self._lang(value)

    def onInit(self):

        # The flag is put in place as root when a device's support ends. The
        # message is shown once, which osmc records in its home, so it needs no
        # sudo. Older versions wrote '1' into the flag itself; that still counts.
        if os.path.isfile(END_OF_LIFE_FLAG) and not os.path.isfile(END_OF_LIFE_SHOWN):
            with open(END_OF_LIFE_FLAG, 'r', encoding='utf-8') as file_handle:
                eol_read = file_handle.readline(1)
            if eol_read != '1':
                _ = xbmcgui.Dialog().ok(self.lang(32083), self.lang(32084))
                try:
                    with open(END_OF_LIFE_SHOWN, 'w', encoding='utf-8') as _:
                        log('%s written' % END_OF_LIFE_SHOWN)
                except OSError as e:
                    log('Could not record that the end of life message was shown: %s' % e)

        if self.first_run:
            self.first_run = False
            self.populate()

        self.set_focused(None)

    def module_info(self, module):
        """ Label, description and icons of a module, translated where possible """
        instance = module['class_instance']

        label = getattr(instance, 'short_name', '') or ''
        if isinstance(getattr(instance, 'short_name_i18n', None), int):
            label = self.lang(instance.short_name_i18n)

        description = getattr(instance, 'description', '') or ''
        if isinstance(getattr(instance, 'description_i18n', None), int):
            description = self.lang(instance.description_i18n)

        return {
            'ID': module['id'],
            'Label': label,
            'Description': str(description),
            'Icon': instance.unfocused_icon,
            'FocusIcon': instance.focused_icon,
        }

    def populate(self):
        """ Publish the modules as window properties, and as list items when
            the skin's xml has a container with LIST_ID """
        items = []
        for slot, module in enumerate(self.live_modules):
            info = self.module_info(module)
            for key, value in info.items():
                self.setProperty('MyOSMC.%d.%s' % (slot, key), value)

            list_item = xbmcgui.ListItem(label=info['Label'], label2=info['Description'], offscreen=True)
            list_item.setArt({'icon': info['Icon'], 'thumb': info['Icon']})
            list_item.setProperty('ID', info['ID'])
            list_item.setProperty('Slot', str(slot))
            list_item.setProperty('FocusIcon', info['FocusIcon'])
            list_item.setProperty('Description', info['Description'])
            items.append(list_item)

        self.setProperty('MyOSMC.Count', str(len(self.live_modules)))

        try:
            container = self.getControl(LIST_ID)
        except RuntimeError:
            container = None  # the skin's xml uses the slot buttons only

        if container is not None:
            container.reset()
            container.addItems(items)

    def slot_for_control(self, control_id):
        """ The module slot a control stands for, or None """
        if control_id == LIST_ID:
            try:
                return int(self.getControl(LIST_ID).getSelectedItem().getProperty('Slot'))
            except (RuntimeError, AttributeError, ValueError):
                return None

        slot = control_id - SLOT_BASE_ID
        if 0 <= slot < len(self.live_modules):
            return slot
        return None

    def set_focused(self, slot):
        if slot is None:
            self.setProperty('MyOSMC.Focused.Label', self.lang(32002))
            self.setProperty('MyOSMC.Focused.Description', '')
            return
        self.setProperty('MyOSMC.Focused.Label', self.getProperty('MyOSMC.%d.Label' % slot))
        self.setProperty('MyOSMC.Focused.Description', self.getProperty('MyOSMC.%d.Description' % slot))

    def onFocus(self, controlID):
        self.set_focused(self.slot_for_control(controlID))

    def onAction(self, action):
        if action.getId() in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
            self.close()
            return

        # moving within a list container doesn't fire onFocus
        if self.getFocusId() == LIST_ID:
            self.set_focused(self.slot_for_control(LIST_ID))

    def onClick(self, controlID):

        if controlID == CENTER_ID:
            self.close()

        elif controlID == ADVANCED_ID:
            # open the advanced settings beta addon
            xbmc.executebuiltin("RunAddon(script.advancedsettingsetter)")

        else:
            slot = self.slot_for_control(controlID)
            if slot is not None:
                self.launch_module(self.live_modules[slot])

    @staticmethod
    def launch_module(module):
        class_instance = module.get('class_instance', None)

        log('Checking instance: %s ' % str(class_instance))
        if class_instance is None:
            return

        if class_instance.is_alive():
            class_instance.run()
        else:
            class_instance = module['module_instance'].OSMCSettingClass()
            class_instance.daemon = True

            module['class_instance'] = class_instance
            class_instance.start()


class GuiThread(threading.Thread):

    def __init__(self, **kwargs):
        super(GuiThread, self).__init__()

        self.queue = kwargs['queue']
        self._addon = kwargs.get('addon')
        self.window = kwargs.get('window', xbmcgui.Window(10000))
        self.script_path = self.addon.getAddonInfo('path')

        self._hardware_prefix = ''

        self.known_modules_order = {
            "osmcpi": 0,
            "osmcupdates": 1,
            "osmcnetworking": 2,
            "osmclogging": 3,
            "apfstore": 4,
            "osmcservices": 5,
            "osmcremotes": 6,
        }

        self.live_modules = []

        self.module_tally = 1000

        self.gui = None

        self.create_gui()

    @property
    def addon(self):
        if not self._addon:
            self._addon = xbmcaddon.Addon(ADDON_ID)
        return self._addon

    @clog(log)
    def create_gui(self):
        """
            known modules is a list of tuples detailing all the known and permissible modules and services
            (module name, order): the order is the hierarchy of addons (which is used to
            determine the positions of addon in the gui)
        """
        # check if modules and services exist, add the ones that exist to the live_modules list
        ordered_live_modules = self.retrieve_modules()
        ordered_live_modules.sort(key=lambda x: x[0])
        self.live_modules = [x[1] for x in ordered_live_modules]

        # load the modules as widget entries
        self.load_widget_info()

        # instantiate the window; Kodi uses the active skin's copy of XML_FILE
        # if it has one, otherwise the Default one shipped with this add-on
        # (or its -720 twin on 720p skins)
        self.gui = OSMCGui(window_xml(XML_FILE, self.script_path), self.script_path, 'Default', addon=self.addon,
                           window=self.window, live_modules=self.live_modules)

    def load_widget_info(self):
        """ Takes each live_module and loads the information required for it to be included in the MyOSMC widget into the Home window.
        """

        script_location = os.path.join(self.script_path, 'resources', 'lib', 'osmcsettings', 'call_osmc_parent.py')

        self.window.setProperty('MyOSMC.Module.Script', script_location)

        for i, module in enumerate(self.live_modules):
            self.window.setProperty('MyOSMC.Module.%s.name' % i, module['class_instance'].short_name)
            self.window.setProperty('MyOSMC.Module.%s.fo_icon' % i, module['class_instance'].focused_widget)
            self.window.setProperty('MyOSMC.Module.%s.fx_icon' % i, module['class_instance'].unfocused_widget)
            self.window.setProperty('MyOSMC.Module.%s.id' % i, module['id'])
        self.window.setProperty('MyOSMC.Module.Count', str(len(self.live_modules)))

    def close(self):
        """
            Closes the gui
        """

        self.gui.close()

    def run(self):
        """
            Opens the gui window
        """

        log('Opening GUI')
        # pick up colours a skin may have set since the window was built
        apply_theme()
        # display the window
        self.gui.doModal()

        # run the apply_settings method on all modules
        for module in self.live_modules:
            class_instance = module.get('class_instance', False)
            if class_instance:
                try:
                    class_instance.apply_settings()
                except:
                    log('apply_settings failed for %s' % class_instance.addon_id)

        # check is a reboot is required
        reboot = False
        for module in self.live_modules:
            class_instance = module.get('class_instance', False)
            try:
                if class_instance.reboot_required:
                    reboot = True
                    break
            except:
                pass

        if reboot:
            self.queue.put('reboot')

        log('Exiting GUI')

        # start from the centre next time
        try:
            self.gui.setFocusId(CENTER_ID)
        except RuntimeError:
            pass

    @clog(log)
    def retrieve_modules(self):
        """
            Checks to see whether the module exists and is active. If it doesnt exist (or is set to inactive)
            then return False, otherwise import the module (or the setting_module.py in the service or addons
            resources/lib/) and create then return the instance of the SettingGroup in that module.

        """

        self.module_tally = 1000

        known_modules = self.known_modules_order.keys()
        osmc_modules = [x for x in [self.inspect_module(module_name) for module_name in known_modules] if x[1]]

        return osmc_modules

    def inspect_module(self, module_name):
        """
            Checks the provided module to see if it is genuine.
            Returns a tuple.
                (preferred order of module, module name: {unfocused icon, focused icon, instance of OSMCSetting class})
        """

        # if you got this far then this is almost certainly an OSMC setting
        log('Inspecting OSMC Setting module __ %s __' % module_name)
        try:
            if module_name == 'osmcpi' and not self.hardware_prefix.startswith('rbp'):
                return -1, None

            module_instance = __import__('%s.osmc.osmc_setting' % module_name, fromlist=[''])
            class_instance = module_instance.OSMCSettingClass()
            class_instance.daemon = True
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            log('OSMCSetting __ %s __ failed to import' % module_name)
            log(exc_type)
            log(exc_value)
            log(traceback.format_exc())
            return -1, None

        if not (class_instance.unfocused_icon and class_instance.focused_icon and
                class_instance.unfocused_widget and class_instance.focused_widget):
            return -1, None

        log('OSMC Setting module __ %s __ found and imported' % module_name)

        # DETERMINE ORDER OF ADDONS, THIS CAN BE HARDCODED FOR SOME OR THE USER SHOULD BE ABLE TO CHOOSE THEIR OWN ORDER
        if module_name in self.known_modules_order.keys():
            order = self.known_modules_order[module_name]
        else:
            order = self.module_tally
            self.module_tally += 1

        return (order, {
            'id': module_name,
            'class_instance': class_instance,
            'module_instance': module_instance
        })

    @property
    def hardware_prefix(self):
        """ Returns the prefix for the hardware type. rbp, rbp2, etc """

        if self._hardware_prefix:
            return self._hardware_prefix

        self._hardware_prefix = ''

        with open('/proc/cmdline', 'r', encoding='utf-8') as f:
            line = f.readline()

        settings = line.split(' ')

        for setting in settings:
            if setting.startswith('osmcdev='):
                self._hardware_prefix = setting[len('osmcdev='):]
                break

        return self._hardware_prefix
