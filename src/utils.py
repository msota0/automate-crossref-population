import logging
import os

def setup_logging(base_filename, log_dir='logs'):
    """Set up the logger to write logs to a file with a dynamic filename."""
    os.makedirs(log_dir, exist_ok=True)
    
    # Create a log file with the base filename
    log_file = os.path.join(log_dir, f"{base_filename}_xml_generator.log")
    
    # Set up the logging configuration
    logging.basicConfig(
        filename=log_file,  
        level=logging.INFO,  
        format='%(asctime)s - %(levelname)s - %(message)s'  
    )
    logger = logging.getLogger()
    return logger
