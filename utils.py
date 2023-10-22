import subprocess

import docker


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
        table_prefix = ''.join(random.choice(string.ascii_lowercase) for i in range(6))

        # Create the WordPress container
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
            network="1clickwp_network",
            detach=True
        )

        print(container.logs())

        # If multi_site is True, configure it via wp-cli
        if multi_site:
            wp_cli_command = f"docker exec {container.id} wp core multisite-convert"
            subprocess.run(wp_cli_command, shell=True)

        # Define the URL
        site_url = f"http://localhost:{host_port}"

        return site_url



