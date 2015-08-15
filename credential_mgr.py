"""A credential store
"""
import json


class JSONCredentialManager(object):
    """Manage credentials using a JSON file as backing.
    """
    def __init__(self, creds_fname):
        self.creds_fname = creds_fname
        with open(creds_fname) as creds_file:
            self._creds_dict = json.load(creds_file)

    def get_creds(self):
        """Return a 2-tuple of (id, secret)
        """
        return self._creds_dict['id'], self._creds_dict['secret']

    def _dump(self):
        """Dump credentials back to file
        """
        with open(self.creds_fname, 'w') as creds_file:
            json.dump(self._creds_dict, creds_file, sort_keys=True, indent=4)
