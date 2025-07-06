from core.base_container_manager import BaseContainerManager


class PhpMyAdminManager(BaseContainerManager):
    def __init__(self):
        super().__init__(
            name="1clickwp_phpmyadmin",
            image="bitnami/phpmyadmin:latest",
            environment={
                "PHPMYADMIN_DATABASE_HOST": "1clickwp_db",
                "PHPMYADMIN_ALLOW_NO_PASSWORD": "yes"
            },
            labels={
                "traefik.enable": "true",
                "traefik.http.routers.phpmyadmin.rule": "Host(`db.localhost`)",
                "traefik.http.routers.phpmyadmin.entrypoints": "websecure",
                "traefik.http.routers.phpmyadmin.tls": "true",
                "traefik.http.services.phpmyadmin.loadbalancer.server.port": "8080"
            }
        )
