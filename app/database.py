from http.client import HTTPException

DB_CONTAINER_NAME = "1clickwp_db"
from python_on_whales import docker

class Database:
    def delete(self, db_name: str):
        try:
            docker.container.execute(
                container=DB_CONTAINER_NAME,
                command=[
                    'mysql',
                    '-uroot',
                    '-plocal',
                    '-e',
                    f"DROP DATABASE IF EXISTS `{db_name}`;"
                ]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"MySQL error: {str(e)}")

    def create(self, db_name: str):
        try:
            docker.container.execute(
                container=DB_CONTAINER_NAME,
                command=[
                    'mysql',
                    '-uroot',
                    '-plocal',
                    '-e',
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}`;"
                ]
            )
        except Exception as e:
            raise HTTPException(e)