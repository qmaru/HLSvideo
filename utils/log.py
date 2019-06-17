import logging


def log(mode, *para):
    logging.basicConfig(
        level=logging.NOTSET, format='%(asctime)s - %(filename)s [%(levelname)s] %(message)s')
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    log = getattr(logging, mode)
    para = [str(i) for i in para]
    msg = " - ".join(para)
    log(msg)
