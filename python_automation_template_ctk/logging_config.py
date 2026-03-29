import logging

# create a custom logger
logger = logging.getLogger("python_automation_template")
logger.setLevel(logging.DEBUG)

# create handlers
file_handler = logging.FileHandler("python_automation_template.log", mode="w")
console_handler = logging.StreamHandler()

# set level for the handler
file_handler.setLevel(logging.DEBUG)
console_handler.setLevel(logging.INFO)


# create formatters and add them to the handlers
file_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
console_formatter = logging.Formatter("%(levelname)s - %(message)s")

file_handler.setFormatter(file_formatter)
console_handler.setFormatter(console_formatter)


# add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)
