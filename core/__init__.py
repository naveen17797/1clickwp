from core.db_manager import DBManager
from core.phpmyadmin_manager import PhpMyAdminManager
from core.proxy import Proxy


class Core:
    def init(self):
        Proxy().init()
        DBManager().ensure_running()
        PhpMyAdminManager().ensure_running()