#!/bin/env python
import os
import pathlib
import shutil
import subprocess
from datetime import datetime
import logging
import errno

logging.basicConfig(level=logging.DEBUG)

SQUID_PROC_NAME = "squid"

PYTHON_CMD = "/bin/python3"
#PYTHON_CMD = shutil.which('python')
if not PYTHON_CMD:
    PYTHON_CMD = shutil.which('python3')

SQUID_CMD = "/sbin/squid"
#SQUID_CMD = shutil.which('squid')
if not SQUID_CMD:
    logging.fatal(f"Could not locate squid executable in PATH: {os.environ.get('PATH', '')}")
    exit(errno.EPERM)

TENANCY = "mycompany"
OUTPUT_TYPE = "SQUIDCONFIG"
OUTPUT_TEMPLATE = "/opt/m365-squid/squid.conf.template"
OUTPUT_FILE_PATH = "/opt/m365-squid/squid.conf"
LINESEP = "LF"

LOG_PATH = "/opt/m365-squid/logs/"
LOG_FILE_NAME = f"m365-squid-{TENANCY}-{datetime.now().strftime('%Y%m%d%H%M%S')}.log"
LOG_FILE_PATH = f"{LOG_PATH}{LOG_FILE_NAME}"

M365_DIGESTER_CMD = "/opt/m365-endpoint-api-digester/m365digester-cli"

EXTRA_DOMAINS = f"{TENANCY}-files.sharepoint.com " \
                f"{TENANCY}-my.sharepoint.com " \
                f"{TENANCY}-myfiles.sharepoint.come " \
                f"{TENANCY}.sharepoint.com " \
                f"*.live.com " \
                f"autodiscover.{TENANCY}.mail.onmicrosoft.com"

EXCLUDE_DOMAINS = "autodiscover.*.onmicrosoft.com"

DIGESTER_OPTS = f"-C " \
                f"-z Allow Default " \
                f"-e {EXTRA_DOMAINS} " \
                f"-x {EXCLUDE_DOMAINS} " \
                f"-t {OUTPUT_TYPE} " \
                f"--output-template {OUTPUT_TEMPLATE} " \
                f"--linesep {LINESEP} " \
                f"-o {OUTPUT_FILE_PATH}"



if not os.path.isfile(OUTPUT_TEMPLATE):
    logging.fatal(f"Output template '{OUTPUT_TEMPLATE}' file does not exist.")
    exit(errno.ENOENT)

if os.path.isfile(OUTPUT_FILE_PATH):
    logging.warn(f"Overwriting existing output file '{OUTPUT_FILE_PATH}'")

if not os.path.isfile(M365_DIGESTER_CMD):
    logging.fatal(f"Could not locate executable for m365-endpoint-api-digester '{M365_DIGESTER_CMD}'")
    exit(errno.ENOENT)



return_code = -1
try:
    CMD = f"{PYTHON_CMD} {M365_DIGESTER_CMD} {DIGESTER_OPTS}"
    logging.debug(f"Executing: {CMD}")
    return_code = subprocess.call(CMD.split())
except (OSError, subprocess.CalledProcessError) as exception:
    logging.fatal(f"Unable to complete subprocess to m365-endpoint-api-digester. "
                  f"Error: {exception.__class__.__name} {str(exception)}")
    exit(1)

if return_code:
    logging.fatal(f"Subprocess m365-endpoint-api-digester returned error code '{return_code}'.")
    exit(return_code)

logging.info("Running squid pre-flight check")

SQUID_OPTS = f"-k parse " \
             f"-f {OUTPUT_FILE_PATH}"

CMD = f"{SQUID_CMD} {SQUID_OPTS}"
return_code = -1
try:
    logging.debug(f"Executing: '{CMD}'")
    return_code = subprocess.call(CMD.split())
except (OSError, subprocess.CalledProcessError) as exception:
    logging.fatal(f"Unable to complete subprocess to squid. "
                  f"Error: {exception.__class__.__name} {str(exception)}")
    exit(1)

if return_code:
    logging.fatal(f"Subprocess squid returned error code '{return_code}'.")
    exit(return_code)

# everything seems ok...
# try to restart squid?

SQUID_OPTS = f"-k reconfigure"
CMD = f"{SQUID_CMD} {SQUID_OPTS}"

return_code = -1
for proc in psutil.process_iter():
    try:
        if SQUID_PROC_NAME.lower() in proc.name().lower():
            # squid is running...
            try:
                logging.debug(f"Executing: '{CMD}'")
                return_code = subprocess.call(CMD.split())
                break
            except (OSError, subprocess.CalledProcessError) as exception:
                logging.fatal(f"Unable to complete subprocess to squid. "
                              f"Error: {exception.__class__.__name} {str(exception)}")
    except Exception as e:
        # squid might not be running...
        logging.fatal(f"Unable to find squid process {e.__class__.__name} {str(e)}")
        exit(1)

if return_code == -1:
    logging.fatal("Squid is not running!")
    exit(1)

if return_code:
    logging.fatal(f"Subprocess {CMD} returned error code '{return_code}'.")
    exit(return_code)

exit(0)
