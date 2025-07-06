from core.base_container_manager import BaseContainerManager


class DBManager(BaseContainerManager):
    def __init__(self):
        super().__init__(
            name="1clickwp_db",
            image="bitnami/mysql:8.0",
            ports={"3306/tcp": 3306},
            environment={
                "MYSQL_ROOT_PASSWORD": "rootpass",
                "MYSQL_USER": "wpuser",
                "MYSQL_PASSWORD": "wppass",
                "ALLOW_EMPTY_PASSWORD": "no"
            },
            volumes={
                "1clickwp_db_data": {"bind": "/bitnami/mysql", "mode": "rw"}
            }
        )
