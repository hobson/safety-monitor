import glob
import logging
import logging.handlers
import sys

# DEBUG=10, INFO=20, CRITICAL=50
LEVELS = {'debug': logging.DEBUG, 
          'info': logging.INFO,   
          'warning': logging.WARNING,   
          'error': logging.ERROR,       
          'critical': logging.CRITICAL} 

if len(sys.argv) > 1:
  logging.basicConfig(level=LEVELS.get(sys.argv[1], logging.NOTSET))
  print "Command arguments used to set logging level to",sys.argv[1]
else:
  logging.basicConfig(level=logging.DEBUG)
   
log = logging.getLogger("log") # "log" is just a name for labeling the messages, can leave blank to use "root" 
#log.setLevel(logging.DEBUG)
log_file_handler = logging.handlers.RotatingFileHandler("log.txt", maxBytes=40000, backupCount=1)
#log_file_handler.setLevel(logging.DEBUG)
log.addHandler(log_file_handler)

#the log_file_handler also outputs debug messages to the console already, so this just duplicates every line on the console it without the LOG:DEBUG prefix
#log_console_handler = logging.StreamHandler()
#log_console_handler.setLevel(logging.DEBUG)
#log.addHandler(log_console_handler)

log.debug("-"*77)
log.debug("Starting message logger")

def test():
  #log.setLevel(logging.INFO)
  log.debug("Debug message test.")
  log.info("Info message test.")
  log.warning("Warning message test.")
  log.error("Error message test.")
  log.critical("Critical message test.")

if __name__ == "__main__":
  test()
