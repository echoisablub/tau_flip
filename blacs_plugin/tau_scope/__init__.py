"""Save the scope trace of every tau_flip_labscript shot as CSV.

Enabled with `tau_scope = True` under [BLACS/plugins] in the labconfig. Acts on shots in
<experiment_shot_storage>\\tau_flip_labscript whose global SAVE_SCOPE_TRACE is true. The
CSV goes to the same relative path under tau_flip_csv, with the same name as the shot.

The scope is armed right before the shot starts, and the queue waits for the export to
finish, so the next shot can't overwrite the acquisition during the read-out.
"""
import logging
import subprocess
import sys
import threading
from pathlib import Path

import labscript_utils.h5_lock
import h5py
from labscript_utils.labconfig import LabConfig

name = "tau_scope"
module = "tau_scope"
logger = logging.getLogger('BLACS.plugin.%s' % module)

ARM_TIMEOUT = 30
EXPORT_TIMEOUT = 600


class Plugin(object):
    def __init__(self, initial_settings):
        self.menu = None
        self.notifications = {}
        self.initial_settings = initial_settings
        self.BLACS = None
        self.proc = None
        self.reader = None
        self.armed = threading.Event()
        config = LabConfig()
        self.storage = Path(config.get('DEFAULT', 'experiment_shot_storage'))
        self.script = Path(config.get('DEFAULT', 'labscriptlib')) / 'Scripts' / 'tau_scope_csv.py'
        self.python = Path(sys.prefix) / 'Scripts' / 'python.exe'

    def plugin_setup_complete(self, BLACS):
        self.BLACS = BLACS

    def get_save_data(self):
        return {}

    def get_menu_class(self):
        return None

    def get_notification_classes(self):
        return []

    def get_setting_classes(self):
        return []

    def set_menu_instance(self, menu):
        self.menu = menu

    def set_notification_instances(self, notifications):
        self.notifications = notifications

    def get_callbacks(self):
        return {
            'science_starting': self.science_starting,
            'shot_complete': self.shot_complete,
        }

    def _csv_path(self, h5_filepath):
        """Output path for this shot, or None if it shouldn't be saved."""
        for shots, traces in (('tau_flip_labscript', 'tau_flip_csv'), ('gray_scan_labscript', 'gray_scan_csv')):
            try:
                relative = Path(h5_filepath).relative_to(self.storage / shots)
            except ValueError:
                continue
            with h5py.File(h5_filepath, 'r') as f:
                if not f['globals'].attrs.get('SAVE_SCOPE_TRACE', 0):
                    return None
            return (self.storage / traces / relative).with_suffix('.csv')
        return None

    def _stop_export(self):
        """Clean up an export left over from an aborted shot."""
        if self.proc is None:
            return
        if self.proc.poll() is None:
            logger.warning('Stopping unfinished scope export')
            self.proc.kill()
        self.proc.wait()
        self.reader.join()
        self.proc = None

    def _read_output(self, proc):
        for line in proc.stdout:
            line = line.strip()
            logger.info('tau_scope_csv: %s', line)
            if line == 'ARMED':
                self.armed.set()

    def science_starting(self, h5_filepath):
        self._stop_export()
        out_path = self._csv_path(h5_filepath)
        if out_path is None:
            return
        self.armed.clear()
        self.proc = subprocess.Popen(
            [str(self.python), '-u', str(self.script), '--arm', str(out_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self.reader = threading.Thread(target=self._read_output, args=(self.proc,), daemon=True)
        self.reader.start()
        if not self.armed.wait(ARM_TIMEOUT):
            logger.error('Scope not armed after %s s, no trace for %s', ARM_TIMEOUT, h5_filepath)

    def shot_complete(self, h5_filepath):
        if self.proc is None:
            return
        try:
            code = self.proc.wait(EXPORT_TIMEOUT)
        except subprocess.TimeoutExpired:
            logger.error('Scope export timed out for %s', h5_filepath)
            self._stop_export()
            return
        self.reader.join()
        self.proc = None
        if code == 0:
            logger.info('Scope trace saved for %s', h5_filepath)
        else:
            logger.error('Scope export failed for %s (exit code %s)', h5_filepath, code)

    def close(self):
        self._stop_export()
