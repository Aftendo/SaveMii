# SaveMii
NNID Archiver Service (source code)
## How do I setup this?
This is a standard Django app,
But if you really need steps, here you go :
### Step one
- Clone the repository : `git clone https://github.com/LetsShop3DS/SaveMii.git`
- Do `cd SaveMii`
- Create the database ! `python3 manage.py makemigrations miiapp`
- Migrate it : `python3 manage.py migrate`
- Now for the CSS/JS : `python3 manage.py collectstatic` and type "yes"
- Now run the server with `python3 manage.py runserver IP-HERE:8000` for developpement and `python3 manage.py runserver IP-HERE:80` for production.
### DISCLAIMER
This is a Linux tutorial, but if you are on Windows, do it via WSL : https://aka.ms/wsl/
## Screenshot
![](https://raw.githubusercontent.com/LetsShop3DS/SaveMii/main/screen.png)
