#!/usr/bin/env python

import argparse
import logging
from collections import namedtuple
import os
import sys
import shutil
import tkinter
import threading
from tkinter import filedialog
from tkinter import messagebox

APPLICATION_TITLE = 'Organize photos for iOS'

SEPARATOR = ' = '  # Works in iOS
MESSAGE_HIGHLIGHT = '---'
# source_dir = os.path.abspath('h:/temp/test')
# target_dir = os.path.abspath('h:/temp/test-albums')
source_dir = os.path.abspath('h:/Saját/MAIN/Fénykép')
target_dir = os.path.abspath('h:/Saját/MAIN/Photos for iOS')

EXCLUDE_DIRS = [
    'iPod Photo Cache'
]

logger = logging.getLogger('structphoto')


def run_cli(arguments: argparse.Namespace) -> None:
    print('Source directory is: ' + source_dir)
    print('Target directory is: ' + target_dir)
    print('Excluded directories are: ' + ', '.join(str(ed) for ed in EXCLUDE_DIRS))
    print('Everything will be deleted in folder ' + target_dir + '. THIS CANNOT BE UNDONE!!!')
    confirmation = input('Are you REALLY sure? (Y/N) [N]: ')

    if confirmation.upper() == 'Y':
        if arguments.clean:
            CleanupThread(None).execute_with_callback()
        elif arguments.update:
            UpdateThread(None).execute_with_callback()


def run_gui() -> None:
    app = StructPhotoGUI(None)
    app.mainloop()

class DefaultStoppableThread(threading.Thread):

    def __init__(self, finish_msg: str, term_msg: str, target = None, callback=None, callback_args=None) -> None:
        # target = kwargs.pop('target')
        super().__init__(target=self.execute_with_callback)
        Params = namedtuple('Params', ['finish_msg', 'term_msg', 'method', 'callback', 'callback_args'])
        self.params = Params(finish_msg=finish_msg, term_msg=term_msg, method=target, callback=callback, callback_args=callback_args)
        self._stopped = False

    def execute_with_callback(self) -> None:
        self.params.method()
        self._print_finish_message()
        if self.params.callback is not None:
            self.params.callback(*self.params.callback_args)

    def stop(self) -> None:
        self._stopped = True

    @property
    def stopped(self) -> bool:
        return self._stopped

    def _print_finish_message(self):
        if self.stopped:
            self.print_message(self.params.term_msg)
        else:
            self.print_message(self.params.finish_msg)

    @classmethod
    def print_message(cls, toPrint: str) -> None:
        print(MESSAGE_HIGHLIGHT + ' ' + toPrint + ' ' + MESSAGE_HIGHLIGHT)


class CleanupThread(DefaultStoppableThread):
    def __init__(self, callback=None, callback_args=None) -> None:
        super().__init__(finish_msg='Cleanup DONE', term_msg='Cleanup TERMINATED', target=self._clean,
                         callback=callback, callback_args=callback_args)

    def _clean(self) -> None:
        self.print_message('Cleaning folder...')
        for f in os.listdir(target_dir):
            print(f)
            subpath = os.path.join(target_dir, f)
            try:
                if os.path.isdir(subpath) and not f in EXCLUDE_DIRS:
                    shutil.rmtree(subpath)
                elif os.path.isfile(subpath):
                    os.remove(subpath)
            except Exception:
                logger.exception("Error during clean!")
                self.stop()
            if self.stopped:
                break


class UpdateThread(DefaultStoppableThread):
    def __init__(self, callback=None, callback_args=None) -> None:
        super().__init__(finish_msg='Hardlink creation DONE', term_msg='Hardlink creation TERMINATED',
                         target=self._update, callback=callback, callback_args=callback_args)
        self.cleanup_thread = CleanupThread()

    def _update(self) -> None:
        self.cleanup_thread.execute_with_callback()
        if (self.stopped):
            return

        self.print_message('Creating hardlinks...')
        sourcedir_splitted = os.path.normpath(source_dir).split(os.sep)

        for subdir, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            # No subdir
            if not dirs or files:
                subdir_splitted = os.path.normpath(subdir).split(os.sep)
                subdirs_to_merge = subdir_splitted[len(sourcedir_splitted):]
                converted_dir_name = SEPARATOR.join(subdirs_to_merge)

                try:
                    os.makedirs(os.path.join(target_dir, converted_dir_name))
                    print(converted_dir_name)

                    for file in files:
                        os.link(os.path.join(subdir, file), os.path.join(target_dir, converted_dir_name, file))
                        if self.stopped:
                            break
                except Exception:
                    logger.exception("Error during update!")

                if self.stopped:
                    break

    def stop(self):
        super().stop()
        self.cleanup_thread.stop()


class StructPhotoGUI(tkinter.Tk):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.work_thread = None
        self.initialize()

    def initialize(self):
        self.title(APPLICATION_TITLE)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.grid()

        self.e_source_dir_entryVariable = tkinter.StringVar()
        self.e_source_dir = tkinter.Entry(self, textvariable=self.e_source_dir_entryVariable)
        self.e_source_dir.grid(column=0, row=0, columnspan=2, sticky='EW', pady=10)
        self.e_source_dir_entryVariable.set(source_dir)

        b_source_dir = tkinter.Button(self, text=u"Select source directory...", command=self.OnSourceDirButtonClick)
        b_source_dir.grid(column=3, row=0, sticky='EW', pady=10)

        self.e_target_dir_entryVariable = tkinter.StringVar()
        self.e_target_dir = tkinter.Entry(self, textvariable=self.e_target_dir_entryVariable)
        self.e_target_dir.grid(column=0, row=1, columnspan=2, sticky='EW', pady=10)
        self.e_target_dir_entryVariable.set(target_dir)

        b_target_dir = tkinter.Button(self, text=u"Select target directory...", command=self.OnTargetDirButtonClick)
        b_target_dir.grid(column=3, row=1, sticky='EW', pady=10)

        self.output_text_area = tkinter.Text()
        self.output_text_area.grid(column=0, row=3, columnspan=3, rowspan=3, sticky='EW', pady=10)

        #create a Scrollbar and associate it with txt
        scrollb = tkinter.Scrollbar(self, command=self.output_text_area.yview)
        scrollb.grid(row=3, column=2, rowspan=3, sticky='nsew')
        self.output_text_area['yscrollcommand'] = scrollb.set

        self.b_clean = tkinter.Button(self, text=u"Clean", command=self.OnCleanButtonClick)
        self.b_clean.grid(column=3, row=3, sticky='EW')

        self.b_update = tkinter.Button(self, text=u"Update", command=self.OnUpdateButtonClick)
        self.b_update.grid(column=3, row=4, sticky='EW')

        self.b_cancel = tkinter.Button(self, text=u"Cancel", command=self.OnCancelButtonClick)
        self.b_cancel.grid(column=3, row=5, sticky='EW')

        self.grid_columnconfigure(0, weight=1)
        self.geometry("700x600")  # You want the size of the app to be this
        self.resizable(True, True)
        sys.stdout = StdoutRedirector(self.output_text_area)

        self.switch_button_enable(running=False)

    def OnSourceDirButtonClick(self):
        self.SelectDirectory(self.e_source_dir_entryVariable)

    def OnTargetDirButtonClick(self):
        self.SelectDirectory(self.e_target_dir_entryVariable)

    def SelectDirectory(self, entryVariable: tkinter.StringVar):
        directory = filedialog.askdirectory()
        if directory is not None and os.path.isdir(directory):
            entryVariable.set(directory)

    def OnCleanButtonClick(self):
        if self.confirm_delete() is True:
            self.refreshSourceAndTargetDir()
            self.work_thread = CleanupThread(callback=self.switch_button_enable, callback_args=(False,))
            self.work_thread.start()

    def OnUpdateButtonClick(self):
        if self.confirm_delete() is True:
            self.refreshSourceAndTargetDir()
            self.work_thread = UpdateThread(callback=self.switch_button_enable, callback_args=(False,))
            self.work_thread.start()


    def OnCancelButtonClick(self):
        self.work_thread.stop()

    def on_closing(self):
        sys.stdout = sys.__stdout__
        self.destroy()


    def refreshSourceAndTargetDir(self):
        global source_dir
        global target_dir
        self.switch_button_enable(running=True)
        source_dir = os.path.abspath(self.e_source_dir_entryVariable.get())
        target_dir = os.path.abspath(self.e_target_dir_entryVariable.get())


    def switch_button_enable(self, running: bool):
        if running:
            self.output_text_area.delete(1.0,tkinter.END)
            self.b_clean.config(state=tkinter.DISABLED)
            self.b_update.config(state=tkinter.DISABLED)
            self.b_cancel.config(state=tkinter.NORMAL)
        else:
            self.work_thread = None
            self.b_clean.config(state=tkinter.NORMAL)
            self.b_update.config(state=tkinter.NORMAL)
            self.b_cancel.config(state=tkinter.DISABLED)


    @staticmethod
    def confirm_delete():
        global target_dir
        return messagebox.askokcancel("Confirmation to delete",
                                      'Everything will be deleted in folder ' + target_dir + '\r\n THIS CANNOT BE UNDONE!!!\r\n' + 'Are you REALLY sure?')


class IORedirector:
    '''A general class for redirecting I/O to this Text widget.'''

    def __init__(self, text_area):
        self.text_area = text_area


class StdoutRedirector(IORedirector):
    '''A class for redirecting stdout to this Text widget.'''

    def write(self, string: str) -> None:
        self.text_area.insert(tkinter.END, string)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=APPLICATION_TITLE)
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
        source_dir = os.path.abspath(args.source)

    if args.target:
        target_dir = os.path.abspath(args.target)

    if args.gui:
        run_gui()
    else:
        run_cli(args)
