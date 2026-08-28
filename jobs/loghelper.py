# -*- coding: utf-8 -*-
import os
import logging
from logging import handlers

# Log root path
# import read_config

# LOG_ROOT = read_config.log_path
LOG_ROOT = './log'
if not os.path.exists(LOG_ROOT):
    os.makedirs(LOG_ROOT)


def get_logger(log_filename, level=logging.INFO, when='D', back_count=0):
    """
    :brief: Log recording
    :param log_filename: Log file name
    :param level: Log level
    :param when: Interval time:
        S: seconds
        M: minutes
        H: hours
        D: days
        W: weekly (interval==0 means Monday)
        midnight: every midnight
    :param back_count: Number of backup files, if exceeded, automatically delete
    :return: logger
    """
    logger = logging.getLogger(log_filename)
    logger.setLevel(level)
    log_file_path = os.path.join(LOG_ROOT, log_filename)
    # Log output format
    formatter = logging.Formatter('%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')
    # Output to console
    ch = logging.StreamHandler()
    ch.setLevel(level)
    # Output to file
    fh = logging.handlers.TimedRotatingFileHandler(
        filename=log_file_path,
        when=when,
        backupCount=back_count,
        encoding='utf-8')
    fh.setLevel(level)
    # Set log output format
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # Add to logger object
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger
