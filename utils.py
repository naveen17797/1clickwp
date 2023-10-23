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


        # If multi_site is True, configure it via wp-cli
        if multi_site:
            # Check if WP-CLI is installed
            wp_cli_check_command = f"docker exec {container.id} wp --version"
            wp_cli_check_process = subprocess.run(wp_cli_check_command, shell=True, capture_output=True)

            if wp_cli_check_process.returncode == 0:
                # WP-CLI is installed, proceed with multisite conversion
                wp_cli_command = f"docker exec {container.id} wp core multisite-convert"
                subprocess.run(wp_cli_command, shell=True)
            else:
                # WP-CLI is not installed, install it and then run multisite command
                install_wp_cli_command = f"docker exec {container.id} curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar && chmod +x wp-cli.phar && sudo mv wp-cli.phar /usr/local/bin/wp"
                subprocess.run(install_wp_cli_command, shell=True)
                wp_cli_command = f"docker exec {container.id} wp core multisite-convert"
                subprocess.run(wp_cli_command, shell=True)

        # Define the URL
        site_url = f"http://localhost:{host_port}"

        # Assuming site_url is already defined
        install_endpoint = f"{site_url}/wp-admin/install.php?step=2"

        # Define headers and form data
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': site_url,
            'Connection': 'keep-alive',
            'Referer': f"{site_url}/wp-admin/install.php?step=1",
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1'
        }

        form_data = {
            'weblog_title': 'test',
            'user_name': 'admin',
            'admin_password': 'password',
            'admin_password2': 'password',
            'pw_weak': 'on',
            'admin_email': 'admin@example.org',
            'Submit': 'Install WordPress',
            'language': ''
        }

        # Wait for the endpoint to be ready
        max_attempts = 10
        current_attempt = 0

        while current_attempt < max_attempts:
            try:
                response = requests.get(install_endpoint)
                if response.status_code == 200:
                    break
            except Exception as e:
                print(f"Error: {e}")

            current_attempt += 1
            time.sleep(5)  # Wait for 5 seconds before re-attempting

        # Continue with the installation process
        if current_attempt < max_attempts:
            response = requests.post(install_endpoint, headers=headers, data=form_data, timeout=300)
        else:
            print("Endpoint did not become ready within the specified attempts.")

        return site_url, container.attrs['Id']

    def delete_instance(self, site_id):
        container = self.client.containers.get(site_id)
        if container:

            container.kill()
            container.remove()
