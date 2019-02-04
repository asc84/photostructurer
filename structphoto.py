#!/usr/bin/env python

import argparse
import os
import sys
import shutil
import tkinter
import threading
from tkinter import filedialog
from tkinter import messagebox

APPLICATION_TITLE = 'Organize photos for iOS - Please run it as administrator!'

SEPARATOR = ' = '  # Works in iOS
# source_dir = os.path.abspath('h:/temp/test')
# target_dir = os.path.abspath('h:/temp/test-albums')
source_dir = os.path.abspath('h:/Saját/MAIN/Fénykép')
target_dir = os.path.abspath('h:/Saját/MAIN/Photos for iOS')

EXCLUDE_DIRS = [
    'iPod Photo Cache'
]


def run_cli(arguments):
    print('Source directory is: ' + source_dir)
    print('Target directory is: ' + target_dir)
    print('Excluded directories are: ' + ', '.join(str(ed) for ed in EXCLUDE_DIRS))
    print('Everything will be deleted in folder ' + target_dir + '. THIS CANNOT BE UNDONE!!!')
    confirmation = input('Are you REALLY sure? (Y/N) [N]: ')

    if confirmation.upper() == 'Y':
        if arguments.clean:
            cleanup()
        elif arguments.update:
            update()


def run_gui():
    app = StructPhotoGUI(None)
    app.mainloop()


def cleanup():
    print('--- Cleaning folder... ---')
    for f in os.listdir(target_dir):
        print(f)
        subpath = os.path.join(target_dir, f)
        if os.path.isdir(subpath) and not f in EXCLUDE_DIRS:
            shutil.rmtree(subpath)
        if os.path.isfile(subpath):
            os.remove(subpath)
    print('--- Cleanup DONE ---')


def update():
    cleanup()
    print('--- Creating hardlinks... ---')
    sourcedir_splitted = os.path.normpath(source_dir).split(os.sep)

    for subdir, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        # No subdir
        if not dirs or files:
            subdir_splitted = os.path.normpath(subdir).split(os.sep)
            subdirs_to_merge = subdir_splitted[len(sourcedir_splitted):]
            converted_dir_name = SEPARATOR.join(subdirs_to_merge)

            os.makedirs(os.path.join(target_dir, converted_dir_name))
            print(converted_dir_name)

            for file in files:
                os.link(os.path.join(subdir, file), os.path.join(target_dir, converted_dir_name, file))
    print('--- Hardlink creation DONE ---')


class StructPhotoGUI(tkinter.Tk):
    def __init__(self, parent):
        tkinter.Tk.__init__(self, parent)
        self.parent = parent
        self.initialize()

    def initialize(self):
        self.title(APPLICATION_TITLE)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.grid()

        self.e_source_dir_entryVariable = tkinter.StringVar()
        self.e_source_dir = tkinter.Entry(self, textvariable=self.e_source_dir_entryVariable)
        self.e_source_dir.grid(column=0, row=0, sticky='EW', pady=10)
        self.e_source_dir_entryVariable.set(source_dir)

        b_source_dir = tkinter.Button(self, text=u"Select source directory...", command=self.OnSourceDirButtonClick)
        b_source_dir.grid(column=1, row=0, sticky='EW', pady=10)

        self.e_target_dir_entryVariable = tkinter.StringVar()
        self.e_target_dir = tkinter.Entry(self, textvariable=self.e_target_dir_entryVariable)
        self.e_target_dir.grid(column=0, row=1, sticky='EW', pady=10)
        self.e_target_dir_entryVariable.set(target_dir)

        b_target_dir = tkinter.Button(self, text=u"Select target directory...", command=self.OnTargetDirButtonClick)
        b_target_dir.grid(column=1, row=1, sticky='EW', pady=10)

        self.b_clean = tkinter.Button(self, text=u"Clean", command=self.OnCleanButtonClick)
        self.b_clean.grid(column=0, row=2, padx=10, pady=10)

        self.b_update = tkinter.Button(self, text=u"Update", command=self.OnUpdateButtonClick)
        self.b_update.grid(column=1, row=2, padx=10, pady=10)

        self.b_cancel = tkinter.Button(self, text=u"Cancel", command=self.OnCancelButtonClick)
        self.b_cancel.grid(column=2, row=2, padx=10, pady=10)

        self.output_text_area = tkinter.Text()
        self.output_text_area.grid(column=0, row=3, columnspan=2, sticky='EW', pady=10)

        self.grid_columnconfigure(0, weight=1)
        self.geometry("700x600")  # You want the size of the app to be 500x500
        self.resizable(True, True)
        sys.stdout = StdoutRedirector(self.output_text_area)

        self.work_thread = None

    def OnSourceDirButtonClick(self):
        self.SelectDirectory(self.e_source_dir_entryVariable)

    def OnTargetDirButtonClick(self):
        self.SelectDirectory(self.e_target_dir_entryVariable)

    def SelectDirectory(self, entryVariable):
        directory = filedialog.askdirectory()
        if directory is not None and os.path.isdir(directory):
            entryVariable.set(directory)

    def OnCleanButtonClick(self):
        self.refreshSourceAndTargetDir()
        if self.confirm_delete() is True:
            self.work_thread = threading.Thread(target=self.clean_with_gui)
            self.work_thread.start()

    def OnUpdateButtonClick(self):
        self.refreshSourceAndTargetDir()
        if self.confirm_delete() is True:
            self.work_thread = threading.Thread(target=self.update_with_gui)
            self.work_thread.start()


    def OnCancelButtonClick(self):
        self.work_thread._stop()
        self.switch_button_enable(False)


    def on_closing(self):
        sys.stdout = sys.__stdout__
        self.destroy()


    def refreshSourceAndTargetDir(self):
        global source_dir
        global target_dir
        self.switch_button_enable(True)
        source_dir = os.path.abspath(self.e_source_dir_entryVariable.get())
        target_dir = os.path.abspath(self.e_target_dir_entryVariable.get())


    def update_with_gui(self):
        update()
        self.switch_button_enable(False)


    def clean_with_gui(self):
        cleanup()
        self.switch_button_enable(False)


    def switch_button_enable(self, running: bool):
        if running:
            self.b_clean.config(state=tkinter.DISABLED)
            self.b_update.config(state=tkinter.DISABLED)
            self.b_cancel.config(state=tkinter.NORMAL)
        else:
            self.b_clean.config(state=tkinter.NORMAL)
            self.b_update.config(state=tkinter.NORMAL)
            self.b_cancel.config(state=tkinter.DISABLED)


    @staticmethod
    def confirm_delete():
        global target_dir
        return messagebox.askokcancel("Confirmation to delete",
                                      'Everything will be deleted in folder ' + target_dir + '\r\n THIS CANNOT BE UNDONE!!!\r\n' + 'Are you REALLY sure?')


class IORedirector(object):
    '''A general class for redirecting I/O to this Text widget.'''

    def __init__(self, text_area):
        self.text_area = text_area


class StdoutRedirector(IORedirector):
    '''A class for redirecting stdout to this Text widget.'''

    def write(self, str):
        self.text_area.insert(tkinter.END, str)


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
