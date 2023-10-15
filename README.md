# SaveMii
NNID Archiver Service (source code)
# WARNING
This website contains an auto-archiver which will get every single existing NNID, which could be up to ~720gb of archived data.
## How do I setup this?
This is a standard Django app. You probably should know how to setup one. But if you really need steps, here you go (for development setup only):
- First, clone the repository: `git clone https://github.com/LetsShop3DS/SaveMii.git`
- After that, run `cd SaveMii`
- Now, let's create the database: `python3 manage.py makemigrations miiapp`
- After that, we'll apply the migrations to the database: `python3 manage.py migrate`
- Now, run the server with `python3 manage.py runserver`.
**If everything went well, congrats, you now have a development setup! If it doesn't work, create an issue.**
### DISCLAIMER
This is a Linux tutorial, but if you are on Windows, do it via WSL : https://aka.ms/wsl/
## Screenshot
![](https://raw.githubusercontent.com/LetsShop3DS/SaveMii/main/screen.png)
