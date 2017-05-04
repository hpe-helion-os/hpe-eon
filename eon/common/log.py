#
# (c) Copyright 2015-2017 Hewlett Packard Enterprise Development Company LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

import logging.handlers
import os
import zipfile

from oslo_config import cfg

import eon.openstack.common.log as nova_log

from eon.common.gettextutils import _

_DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)8s [%(name)s] %(message)s"
_DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

generic_log_opts = [
    cfg.StrOpt('logfile_mode',
               default='0640',
               help='Default file mode used when creating log files'),
]

CONF = cfg.CONF
CONF.set_default("log_format", _DEFAULT_LOG_FORMAT)
CONF.set_default("log_date_format", _DEFAULT_LOG_DATE_FORMAT)
CONF.register_opts(generic_log_opts)

logging.AUDIT = logging.INFO + 1
logging.addLevelName(logging.AUDIT, 'AUDIT')


def setup(product_name):
    """Setup logging."""
    nova_log.setup(product_name)


def getLogger(name='unknown', version='unknown'):
    return nova_log.getLogger(name, version)


def mask_password(message):
    return nova_log.mask_password(message)


class EonLogHandler(logging.handlers.RotatingFileHandler):
    """Size based rotating file handler which zips the previous log files
    """
    def __init__(self, filename, mode='a', maxBytes=104857600, backupCount=20,
                 encoding='utf-8'):
        logging.handlers.RotatingFileHandler.__init__(
            self, filename, mode, maxBytes, backupCount, encoding)

    def doRollover(self):
        ''' Keeping the rolled over log files ziped.
        '''
        logging.handlers.RotatingFileHandler.doRollover(self)
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = "%s.%d.gz" % (self.baseFilename, i)
                dfn = "%s.%d.gz" % (self.baseFilename, i + 1)
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = self.baseFilename + ".1"
            compressed_log_file = zipfile.ZipFile(dfn + ".gz", "w")
            compressed_log_file.write(dfn, os.path.basename(
                dfn), zipfile.ZIP_DEFLATED)
            compressed_log_file.close()
            os.remove(dfn)


class DeprecatedConfig(Exception):
    message = (_("Fatal call to deprecated config: %(msg)s"))

    def __init__(self, msg):
        super(Exception, self).__init__(self.message % dict(msg=msg))
