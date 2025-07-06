# What it does?
# Instantly starts up WordPress instances with single click.
# Allow user to create wordpress sites.
# Allow user to assign a domain name to it.
# Allow user to edit the WordPress files.
# Allow user to autologin.
# Allow user to view logs.
# Allow user to explore database.


from fastapi import FastAPI

app = FastAPI()


@app.get("/sites")
async def root():
    return {"message": "Hello World"}