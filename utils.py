import os
import subprocess
import time

import docker
import requests


class DB:
    def __init__(self):
        # Initialize the Docker client
        self.client = docker.from_env()

        # Check if the network already exists
        network_name = "1clickwp_network"
        existing_network = None
        try:
            existing_network = self.client.networks.get(network_name)
        except docker.errors.NotFound:
            pass

        # Create the network only if it doesn't exist
        if existing_network is None:
            self.network = self.client.networks.create(network_name, driver="bridge")
        else:
            self.network = existing_network

    def init_db(self):
        # Check if a container named '1clickwp_db' already exists
        db_container = None
        try:
            db_container = self.client.containers.get('1clickwp_db')
        except docker.errors.NotFound:
            pass

        if db_container is not None and db_container.status == "running":
            print("Container '1clickwp_db' is already running.")
        else:
            # Start the container if it exists but is not running
            if db_container is not None:
                try:
                    db_container.start()
                    print("Container '1clickwp_db' started.")
                except Exception as e:
                    print(f"Error starting container: {e}")
            else:
                # Define container configuration
                container_config = {
                    'image': 'mysql:5.7',
                    'environment': {
                        'MYSQL_ROOT_PASSWORD': 'password',
                        'MYSQL_DATABASE': '1clickwp_db'
                    },
                    'name': '1clickwp_db',
                    'network': '1clickwp_network'
                }

                # Create and start the container
                try:
                    container = self.client.containers.run(**container_config, detach=True)
                    print(f'Container ID: {container.id}')
                except Exception as e:
                    print(f"Error creating container or database: {e}")


class WordPress:
    def __init__(self):
        # Initialize the Docker client
        self.client = docker.from_env()

    def get_instances(self):
        containers = self.client.containers.list()
        return [container for container in containers if container.name.startswith("1clickwp_wp_container_")]

    def wait_for_container_ready(self, container_name):
        while True:
            try:
                container = self.client.containers.get(container_name)
                if container.status == 'running':
                    print(f"Container '{container_name}' is running and ready.")
                    return
            except docker.errors.NotFound:
                pass

            print(f"Waiting for container '{container_name}' to be ready...")
            time.sleep(5)

    def create_instance(self, version, multi_site):
        # Define image name based on provided version
        image_name = f"wordpress:{version}"

        # Find an available host port (e.g., starting from 9000)
        host_port = 10000
        while True:
            try:
                print("cant use port " + str(host_port) + " since its already allocated")
                self.client.containers.get(f"1clickwp_wp_container_{host_port}")
                host_port += 1
            except docker.errors.NotFound:
                break
        print("using port " + str(host_port))
        # Generate a random prefix for tables
        import random
        import string
        table_prefix = ''.join(random.choice(string.ascii_lowercase) for i in range(6)) + str(host_port)

        # Create the WordPress container
        # Create the WordPress container
        deps_path = os.path.abspath('deps')

        container = self.client.containers.run(
            image=image_name,
            name=f"1clickwp_wp_container_{host_port}",
            ports={f"80/tcp": ('127.0.0.1', host_port)},
            environment={
                "WORDPRESS_DB_HOST": "1clickwp_db",
                "WORDPRESS_DB_USER": "root",
                "WORDPRESS_DB_PASSWORD": "password",
                "WORDPRESS_DB_NAME": "1clickwp_db",  # Set the database name
                "WORDPRESS_TABLE_PREFIX": table_prefix  # Set the table prefix
            },
            volumes={
                f"{deps_path}/wp": {"bind": "/usr/local/bin/wp", "mode": "ro"},
                f"{deps_path}/mysql": {"bind": "/usr/bin/mysql", "mode": "ro"},
                f"{deps_path}/libedit.deb": {"bind": "/tmp/libedit.deb", "mode": "ro"}
            },
            network="1clickwp_network",
            detach=True
        )

        """
            First we need to write the config from environment variable to to ~/.wp-cli/config.yml
            Because the official wordpress docker image reads from env variable
            and wp-cli refuses to do it from env variable and requires a yaml file
            ( The reasoning behind this is beyond my intellectual capability ) 
        """
        command_template = '''bash -c "mkdir -p ~/.wp-cli/ && echo -e 'path: /var/www/html\\nurl: http://{WORDPRESS_DB_HOST}\\ndatabase:\\n  dbname: {WORDPRESS_DB_NAME}\\n  user: {WORDPRESS_DB_USER}\\n  password: {WORDPRESS_DB_PASSWORD}\\n  host: {WORDPRESS_DB_HOST}\\n  prefix: {WORDPRESS_TABLE_PREFIX}' > ~/.wp-cli/config.yml"'''

        command = command_template.format(
            WORDPRESS_DB_HOST="1clickwp_db",
            WORDPRESS_DB_NAME="1clickwp_db",
            WORDPRESS_DB_USER="root",
            WORDPRESS_DB_PASSWORD="password",
            WORDPRESS_TABLE_PREFIX=table_prefix
        )

        container.exec_run(command, stdout=True, stderr=True, tty=True)


        # Define the URL
        site_url = f"http://localhost:{host_port}"

        """
         The official wordpress image dont have wp-cli installed, that's ok we can just volume map the wp-cli right ?
         Nope, the wp-cli has another dependency called mysql-client, without that wp-cli wont work.
         Umm ok, couldnt we volume map that stand alone binary since all of the wp images are built on debian ?
         Nope, the mysql-client requires libedit.so, at this point i got quite frustrated. One might ask why dont you
         just install it every time you create the wp container ? This app spawns containers multiple times, i dont want to 
         waste the network bandwidth. So on final try i mapped the libedit.so file and it worked. But deep down i know i created a 
         frankeinsteins monster.
         
         If you are thinking why didn't this guy just extend and publish own image ? The purpose of this app is to test official wp images,
         I dont want to take responsibility to publish new images as the time progress.
        """

        logs = container.exec_run(
            f"bash -c 'dpkg -i /tmp/libedit.deb && wp core install --path=/var/www/html --url={site_url} --title=\"Your Site Title\" --admin_user=admin --admin_password=password --admin_email=admin@example.org --allow-root'",
            stdout=True, stderr=True, tty=True)
        print(logs)

        if multi_site:
            wp_cli_command = f"docker exec {container.id} wp core multisite-convert --allow-root"
            subprocess.run(wp_cli_command, shell=True)


        return site_url, container.attrs['Id']

    def delete_instance(self, site_id):
        container = self.client.containers.get(site_id)
        if container:
            container.kill()
            container.remove()
