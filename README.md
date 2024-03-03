# 1ClickWP 
<span style="padding: 5px 10px; background-color: #4CAF50; color: #000000; font-weight: bold; border-radius: 3px;">
Version: 1.0.5
</span>

![image](https://github.com/naveen17797/1clickwp/assets/18109258/02fd4920-18b6-4a9b-bb78-c5339a995db7)



1ClickWP is a powerful open-source tool that allows you to effortlessly create WordPress sites with just a single click. Whether you need a single WordPress site or a multisite network, 1ClickWP has got you covered.     



## Features

- Single-click WordPress site creation
- Multisite functionality for managing multiple WordPress sites from a single installation
- phpmyadmin available for every site
- Ability to bind local plugin / theme folders in to WP
- Built with FastAPI for blazing-fast performance

### Prerequisites

- Python 3.x installed on your system
- Pip package manager
- Docker ( essential for 1clickwp to work )

### Install Dependencies
```pip install -r requirements.txt```

### Start the application
```
venv/bin/python -m uvicorn main:app --reload --timeout-keep-alive 30000
```
you can now access the ui at
```
http://localhost:8000
```

### Installation via docker
```shell
docker run -p 8000:8000 -v /var/run/docker.sock:/var/run/docker.sock  1clickwp:latest
```


### Screenshots
![image](https://github.com/naveen17797/1clickwp/assets/18109258/58dee895-639a-46fe-b5ab-1c8cfc0fb728)


