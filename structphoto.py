#!/usr/bin/env python

""" Structure Photos in a deep hierarchy into a flat structure using hardlinks.

"""

import argparse
import configparser
import json
import logging
import typing
from collections import namedtuple
import os
import sys
import shutil
import tkinter
import threading
from tkinter import filedialog, messagebox

APPLICATION_TITLE = 'Organize photos for iOS'

LOGGER = logging.getLogger('structphoto')


def run_cli(arguments: argparse.Namespace) -> None:
    """ Run the script on the command line

    """

    print('Source directory is: ' + ConfigHolder().source_dir)
    print('Target directory is: ' + ConfigHolder().target_dir)
    print('Excluded directories are: ' + ', '.join(str(ed) for ed in ConfigHolder().exclude_dirs))
    print('Everything will be deleted in folder ' + ConfigHolder().target_dir + '. THIS CANNOT BE UNDONE!!!')
    confirmation = input('Are you REALLY sure? (Y/N) [N]: ')

    if confirmation.upper() == 'Y':
        if arguments.clean:
            CleanupThread(None).execute_with_callback()
        elif arguments.update:
            UpdateThread(None).execute_with_callback()


def run_gui() -> None:
    """
    Run the script with Tkinter GUI
    """

    app = StructPhotoGUI()
    app.mainloop()


class ConfigHolder():
    """ Class to hold the config
    This is handled as singleton, it will always return the same instance, when trying to instantiate it.

    """

    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            # pylint: disable=protected-access
            cls.__instance.__initialized = False
        return cls.__instance

    def __init__(self):
        # pylint: disable=access-member-before-definition
        if self.__initialized:
            return
        super().__init__()
        self.__initialized = True

        self.separator: str = None
        self.message_highlight: str = None
        self.source_dir: str = None
        self.target_dir: str = None
        self.exclude_dirs: typing.List = []


class DefaultStoppableThread(threading.Thread):
    """ Common sublass of Thread, which is stoppable

    """

    def __init__(self, finish_msg: str, term_msg: str, target=None, callback=None, callback_args=None) -> None:
        super().__init__(target=self.execute_with_callback)
        Params = namedtuple('Params', ['finish_msg', 'term_msg', 'method', 'callback', 'callback_args'])
        self.params = Params(finish_msg=finish_msg, term_msg=term_msg, method=target,
                             callback=callback, callback_args=callback_args)
        self._stopped = False

    def execute_with_callback(self) -> None:
        """
        Execute the method and call the collback function afterwards.
        """

        self.params.method()
        self._print_finish_message()
        if self.params.callback is not None:
            self.params.callback(*self.params.callback_args)

    def stop(self) -> None:
        """
        Indicate a stop request to this instance.
        It will only have effect, if it regularly checks for stopped.
        """

        self._stopped = True

    @property
    def stopped(self) -> bool:
        """
        Check if a stop request has been initiated.
        """

        return self._stopped

    def _print_finish_message(self):
        if self.stopped:
            self.print_message(self.params.term_msg)
        else:
            self.print_message(self.params.finish_msg)

    @classmethod
    def print_message(cls, to_print: str) -> None:
        """
        Print a message in the common format prefixed and suffixed with the message highlight
        """

        print(ConfigHolder().message_highlight + ' ' + to_print + ' ' + ConfigHolder().message_highlight)


class CleanupThread(DefaultStoppableThread):
    """ Class for handling cleanup

    """

    def __init__(self, callback=None, callback_args=None) -> None:
        super().__init__(finish_msg='Cleanup DONE', term_msg='Cleanup TERMINATED', target=self._clean,
                         callback=callback, callback_args=callback_args)

    def _clean(self) -> None:
        self.print_message('Cleaning folder...')
        for file in os.listdir(ConfigHolder().target_dir):
            print(file)
            subpath = os.path.join(ConfigHolder().target_dir, file)
            try:
                if os.path.isdir(subpath) and not file in ConfigHolder().exclude_dirs:
                    shutil.rmtree(subpath)
                elif os.path.isfile(subpath):
                    os.remove(subpath)
            except Exception:
                LOGGER.exception("Error during clean!")
                self.stop()
                raise
            if self.stopped:
                break


class UpdateThread(DefaultStoppableThread):
    """ Class for handling update

    """

    def __init__(self, callback=None, callback_args=None) -> None:
        super().__init__(finish_msg='Hardlink creation DONE', term_msg='Hardlink creation TERMINATED',
                         target=self._update, callback=callback, callback_args=callback_args)
        self.cleanup_thread = CleanupThread()

    def _update(self) -> None:
        self.cleanup_thread.execute_with_callback()
        if self.stopped:
            return

        self.print_message('Creating hardlinks...')
        sourcedir_splitted = os.path.normpath(ConfigHolder().source_dir).split(os.sep)

        for subdir, dirs, files in os.walk(ConfigHolder().source_dir):
            dirs[:] = [d for d in dirs if d not in ConfigHolder().exclude_dirs]

            # No subdir
            if not dirs or files:
                subdir_splitted = os.path.normpath(subdir).split(os.sep)
                subdirs_to_merge = subdir_splitted[len(sourcedir_splitted):]
                converted_dir_name = ConfigHolder().separator.join(subdirs_to_merge)

                try:
                    os.makedirs(os.path.join(ConfigHolder().target_dir, converted_dir_name))
                    print(converted_dir_name)

                    for file in files:
                        os.link(os.path.join(subdir, file), os.path.join(ConfigHolder().target_dir,
                                                                         converted_dir_name, file))
                        if self.stopped:
                            break
                except Exception:
                    LOGGER.exception("Error during update!")
                    self.start()
                    raise

                if self.stopped:
                    break

    def stop(self):
        super().stop()
        self.cleanup_thread.stop()


class StructPhotoGUI(tkinter.Tk):
    """ Class for handling the GUI

    """

    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            # pylint: disable=protected-access
            cls.__instance.__initialized = False
        return cls.__instance

    def __init__(self):
        # pylint: disable=access-member-before-definition
        if self.__initialized:
            return
        super().__init__()
        self.__initialized = True
        self.work_thread = None
        self.__initialize_gui()

    def __initialize_gui(self) -> None:
        """
        Initialize the GUI, create and place all components
        """

        self.title(APPLICATION_TITLE)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.grid()

        self.e_source_dir_entry_variable = tkinter.StringVar()
        self.e_source_dir = tkinter.Entry(self, textvariable=self.e_source_dir_entry_variable)
        self.e_source_dir.grid(column=0, row=0, columnspan=3, sticky='EW', padx=10, pady=10)
        self.e_source_dir_entry_variable.set(ConfigHolder().source_dir)

        b_source_dir = tkinter.Button(self, text=u"Select source directory...",
                                      command=self._on_source_dir_button_click)
        b_source_dir.grid(column=4, row=0, sticky='EW', padx=10, pady=10)

        self.e_target_dir_entry_variable = tkinter.StringVar()
        self.e_target_dir = tkinter.Entry(self, textvariable=self.e_target_dir_entry_variable)
        self.e_target_dir.grid(column=0, row=1, columnspan=3, sticky='EW', padx=10, pady=10)
        self.e_target_dir_entry_variable.set(ConfigHolder().target_dir)

        b_target_dir = tkinter.Button(self, text=u"Select target directory...",
                                      command=self._on_target_dir_button_click)
        b_target_dir.grid(column=4, row=1, sticky='EW', padx=10, pady=10)

        self.output_text_area = tkinter.Text()
        self.output_text_area.grid(column=0, row=3, columnspan=3, rowspan=3, sticky='EW', padx=10, pady=10)

        # create a Scrollbar and associate it with txt
        scrollb = tkinter.Scrollbar(self, command=self.output_text_area.yview)
        scrollb.grid(row=3, column=3, rowspan=3, sticky='nsew')
        self.output_text_area['yscrollcommand'] = scrollb.set

        self.b_clean = tkinter.Button(self, text=u"Clean", command=self._on_clean_button_click)
        self.b_clean.grid(column=4, row=3, sticky='EW', padx=10)

        self.b_update = tkinter.Button(self, text=u"Update", command=self._on_update_button_click)
        self.b_update.grid(column=4, row=4, sticky='EW', padx=10)

        self.b_cancel = tkinter.Button(self, text=u"Cancel", command=self._on_cancel_button_click)
        self.b_cancel.grid(column=4, row=5, sticky='EW', padx=10)

        self.grid_columnconfigure(0, weight=1)
        self.geometry("700x500")  # You want the size of the app to be this
        self.resizable(True, True)
        sys.stdout = IORedirector(self.output_text_area)  # type: ignore

        self._switch_button_enable(running=False)

    def _on_source_dir_button_click(self) -> None:
        self._select_directory(self.e_source_dir_entry_variable)

    def _on_target_dir_button_click(self) -> None:
        self._select_directory(self.e_target_dir_entry_variable)

    @staticmethod
    def _select_directory(entry_variable: tkinter.StringVar) -> None:
        directory = filedialog.askdirectory(initialdir=entry_variable.get())
        if directory is not None and os.path.isdir(directory):
            entry_variable.set(directory)

    def _on_clean_button_click(self) -> None:
        if self._confirm_delete() is True:
            self._refresh_source_and_target_dir()
            self.work_thread = CleanupThread(callback=self._switch_button_enable, callback_args=(False,))
            self.work_thread.start()

    def _on_update_button_click(self) -> None:
        if self._confirm_delete() is True:
            self._refresh_source_and_target_dir()
            self.work_thread = UpdateThread(callback=self._switch_button_enable, callback_args=(False,))
            self.work_thread.start()

    def _on_cancel_button_click(self) -> None:
        self.work_thread.stop()

    def _on_closing(self) -> None:
        sys.stdout = sys.__stdout__
        self.destroy()

    def _refresh_source_and_target_dir(self) -> None:
        self._switch_button_enable(running=True)
        ConfigHolder().source_dir = os.path.abspath(self.e_source_dir_entry_variable.get())
        ConfigHolder().target_dir = os.path.abspath(self.e_target_dir_entry_variable.get())

    def _switch_button_enable(self, running: bool) -> None:
        if running:
            self.output_text_area.delete(1.0, tkinter.END)
            self.b_clean.config(state=tkinter.DISABLED)
            self.b_update.config(state=tkinter.DISABLED)
            self.b_cancel.config(state=tkinter.NORMAL)
        else:
            self.work_thread = None
            self.b_clean.config(state=tkinter.NORMAL)
            self.b_update.config(state=tkinter.NORMAL)
            self.b_cancel.config(state=tkinter.DISABLED)

    @staticmethod
    def _confirm_delete() -> bool:
        return messagebox.askokcancel("Confirmation to delete",
                                      'Everything will be deleted in folder ' + ConfigHolder().target_dir +
                                      '\r\n THIS CANNOT BE UNDONE!!!\r\n' + 'Are you REALLY sure?')


class IORedirector():
    """ A class for redirecting stdout to this Text widget.

    """

    def __init__(self, text_area: tkinter.Text) -> None:
        self.text_area = text_area

    def write(self, string: str) -> int:
        """
        Alternative write method implementation for sys.stdout to call. This will write to a Tkinter text area.
        """
        return self.text_area.insert(tkinter.END, string)


class SpaceAwareConfigParser(configparser.ConfigParser):
    """ A special config parser implementation, which repects leading and trailing spaces.

    Original: https://thekondor.blogspot.com/2011/11/python-make-configparser-aware-of.html
    """
    QUOTE_SYMBOLS = ('"', "'")
    KEEP_SPACES_KEYWORD = "keep_spaces"

    # pylint: disable= redefined-outer-name
    def __init__(self, **args) -> None:
        self.__keep_spaces = args.pop(self.KEEP_SPACES_KEYWORD, True)

        super().__init__(**args)

    # pylint: disable= redefined-outer-name
    def get(self, section, option, **args):
        value = super().get(section, option, **args)
        if self.__keep_spaces:
            value = self._unwrap_quotes(value)

        return value

    def set(self, section: str, option, value: str = None) -> None:
        if self.__keep_spaces:
            value = self._wrap_to_quotes(value)

        super().set(section, option, value)

    @staticmethod
    def _unwrap_quotes(src: str) -> str:
        for quote in SpaceAwareConfigParser.QUOTE_SYMBOLS:
            if src.startswith(quote) and src.endswith(quote):
                return src.strip(quote)

        return src

    @staticmethod
    def _wrap_to_quotes(src: str = None) -> typing.Optional[str]:
        if src and src[0].isspace():
            return '"%s"' % src

        return src


if __name__ == '__main__':
    config: SpaceAwareConfigParser = SpaceAwareConfigParser()
    config.read(['./config/structphoto.ini', '~/.structphoto/structphoto.ini'], 'UTF-8')

    configholder: ConfigHolder = ConfigHolder()
    configholder.separator = config.get("CONSTANTS", "SEPARATOR")
    configholder.message_highlight = config.get("CONSTANTS", "MESSAGE_HIGHLIGHT")
    configholder.source_dir = os.path.abspath(config.get("PATHS", "SOURCE_DIR"))
    configholder.target_dir = os.path.abspath(config.get("PATHS", "TARGET_DIR"))
    configholder.exclude_dirs = json.loads(config.get("PATHS", "EXCLUDE_DIRS"))

    parser: argparse.ArgumentParser = argparse.ArgumentParser(description=APPLICATION_TITLE)
    main_group = parser.add_mutually_exclusive_group(required=True)
    main_group.add_argument('-c', '--clean', action='store_true', help='Clean the target folder only.')
    main_group.add_argument('-u', '--update', action='store_true',
                            help='Clean the target folder only and update the hardlinks.')
    main_group.add_argument('-g', '--gui', action='store_true',
                            help='Run the application with GUI')
    parser.add_argument('-s', '--source', help='Source directory')
    parser.add_argument('-t', '--target', help='Target directory')

    args, leftovers = parser.parse_known_args()

    if args.source:
        configholder.source_dir = os.path.abspath(args.source)

    if args.target:
        configholder.target_dir = os.path.abspath(args.target)

    if args.gui:
        run_gui()
    else:
        run_cli(args)
