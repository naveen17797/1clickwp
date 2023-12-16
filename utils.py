import os
# Generate a random prefix for tables
import random
import string
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
    def init_phpmyadmin(self):
        # Check if a container named '1clickwp_db' already exists
        phpmyadmin_container = None
        try:
            phpmyadmin_container = self.client.containers.get('1clickwp_phpmyadmin')
        except docker.errors.NotFound:
            pass

        if phpmyadmin_container is not None and phpmyadmin_container.status == "running":
            print("Container '1clickwp_phpmyadmin' is already running.")
        else:
            # Start the container if it exists but is not running
            if phpmyadmin_container is not None:
                try:
                    phpmyadmin_container.start()
                    print("Container '1clickwp_phpmyadmin' started.")
                except Exception as e:
                    print(f"Error starting container: {e}")
            else:
                # Define container configuration
                container_config = {
                    'image': 'phpmyadmin:apache',
                    'environment': {
                        'PMA_HOST': '1clickwp_db',
                        'PMA_PORT': '3306',
                        'PMA_USER': 'root',
                        'PMA_PASSWORD': 'password',
                        'MYSQL_ROOT_PASSWORD': 'password'
                    },
                    'name': '1clickwp_phpmyadmin',
                    'network': '1clickwp_network',
                    'ports': {f"80/tcp": ('127.0.0.1', 9999)},
                }

                # Create and start the container
                try:
                    print("Going to create phpmyadmin instance, this might take few mins..")
                    container = self.client.containers.run(**container_config, detach=True)
                    print(f'Container ID: {container.id}')
                except Exception as e:
                    print(f"Error creating container or database: {e}")

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
                    print("Going to start database container, this might take few mins..")
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
                    print("Going to create database container, this might take few mins..")
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



    def create_instance(self, version, multi_site, volume_bindings):
        # Define image name based on provided version
        image_name = f"wordpress:{version}"
        label = 'multi_site' if multi_site else ''
        # Define the prefix
        prefix = "1clickwp_wp_container_"

        # Get a list of containers with the specified prefix
        containers = self.client.containers.list(all=True, filters={"name": f"^/{prefix}"})

        # Extract host ports from container names
        used_ports = [int(container.name.split("_")[-1]) for container in containers]

        if used_ports:
            max_port = max(used_ports)
            host_port = max_port + 1
        else:
            host_port = 10000
        print("using port " + str(host_port))

        table_prefix = ''.join(random.choice(string.ascii_lowercase) for i in range(6)).replace(" ", "") + '_' + str(host_port)

        # Create the WordPress container
        # Create the WordPress container
        deps_path = os.path.abspath('deps')
        volumes = {
                f"{deps_path}/wp": {"bind": "/usr/local/bin/wp", "mode": "ro"},
                f"{deps_path}/mysql": {"bind": "/usr/bin/mysql", "mode": "ro"},
                f"{deps_path}/libedit.deb": {"bind": "/tmp/libedit.deb", "mode": "ro"},
                f"{deps_path}/mu-plugins/load.php": {"bind": "/var/www/html/wp-content/mu-plugins/load.php", "mode": "ro"},
                f"{deps_path}/mu-plugins/auto-login.php": {"bind": "/var/www/html/wp-content/mu-plugins/auto-login.php",
                                                     "mode": "ro"}
            }

        for v in volume_bindings:
            volumes[v.host_path] = {"bind": v.container_path, "mode": "ro"}




        container = self.client.containers.run(
            labels= {
                "table_prefix": table_prefix
            },
            image=image_name,
            name=f"1clickwp_wp_container_{label}_{host_port}",
            ports={f"80/tcp": ('127.0.0.1', host_port)},
            environment={
                "WORDPRESS_DB_HOST": "1clickwp_db",
                "WORDPRESS_DB_USER": "root",
                "WORDPRESS_DB_PASSWORD": "password",
                "WORDPRESS_DB_NAME": "1clickwp_db",  # Set the database name
                "WORDPRESS_TABLE_PREFIX": table_prefix  # Set the table prefix
            },
            volumes=volumes,
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
            f"bash -c 'dpkg -i /tmp/libedit.deb && wp core install --path=/var/www/html --url={site_url} --title=\"Your Site Title\" --admin_user=admin --admin_password=password --admin_email=admin@example.org --allow-root && wp option update permalink_structure '/%postname%/' --allow-root'",
            stdout=True, stderr=True, tty=True)
        print(logs)

        if multi_site:
            wp_cli_command = f"docker exec {container.id} wp core multisite-convert --allow-root"
            subprocess.run(wp_cli_command, shell=True)

        """
        Just another hack to get the cron working since the wp official image cron dont work if we bind it to a custom port
        So this forces apache to listen to host port inside container which is crucial for the cron to work.
        Every Day. We stray further from god's light.
        """
        apache_config_command = '''bash -c "sed -i 's/<VirtualHost \*:80>/<VirtualHost \*:80 *:{}>/' /etc/apache2/sites-enabled/000-default.conf && sed -i '/Listen 80/a Listen {}' /etc/apache2/ports.conf && apachectl restart"'''\
            .format(host_port, host_port)
        container.exec_run(apache_config_command, stdout=True, stderr=True, tty=True)



        return site_url, container.attrs['Id'], table_prefix

    def delete_instance(self, site_id):
        container = self.client.containers.get(site_id)
        if container:
            container.kill()
            container.remove()
