#idk thingy
import os, xmltodict
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'savemii.settings')
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
from miiapp.models import NintendoNetworkID, BlockedNNID
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import OperationalError
from django.utils.timezone import now
from savemii.settings import BASE_DIR, NINTENDO_API_ID, NINTENDO_API_SECRET
from requests import get
import warnings
import io
from PIL import Image

#we're running bois
daemon = open("/tmp/nnid_scrapper_running", "w+")
daemon.close()

try:
    pid = open("pid.txt", "r+")
except FileNotFoundError:
    print("[AutoArchiver] No pid.txt file found; initializing.")
    with open("pid.txt", "w+") as f:
        f.write(str(1799999999))
        f.close()
    pid = open("pid.txt", "r+")

pid.seek(0)

i = int(pid.read())
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        try:
            try:
                print("[AutoArchiver] Started! Now auto archiving PIDs... (this process can take weeks; you can restart it later using CTRL+C)")
                while i >= 1:
                    try:
                        nnid_db = NintendoNetworkID.objects.get(pid=i)
                        i -= 1
                        continue
                    except ObjectDoesNotExist:
                        pass
                    print("[AutoArchiver] Trying PID "+str(i))

                    # use the nintendo network api
                        
                    #default headers, according to https://github.com/kinnay/NintendoClients/wiki/Account-Server
                    headers = {
                        "X-Nintendo-Client-ID": NINTENDO_API_ID,
                        "X-Nintendo-Client-Secret": NINTENDO_API_SECRET
                    }

                    #get mii data with pid
                    url = "https://accountws.nintendo.net/v1/api/miis"
                    payload = {'pids': i}
                    response = get(url, params=payload, headers=headers)
                    if response.status_code == 404:
                        print("[AutoArchiver] NNID not found/deleted; skipping PID "+str(i))
                        i -= 1
                        continue
                    api = xmltodict.parse(response.text)['miis']['mii']
                    nnid = api['user_id']
                    try:
                        is_blocked = BlockedNNID.objects.get(nnid=nnid)
                        i -= 1
                        continue
                    except ObjectDoesNotExist:
                        pass
                    try:
                        api['images']['hash'] = api["images"]["image"][0]["url"].split("/")[-1].split("_")[0]
                    except KeyError:
                        api['images']['hash'] = api["images"]["image"]["url"].split("/")[-1].split("_")[0]
                    pid.truncate(0)
                    pid.seek(0)
                    pid.write(str(i))
                    #else, continue with the archiving process
                    #WARNING: POORLY WRITTEN CODE AHEAD!!
                    # save mii images
                    miis = api['images']['image']
                    if not os.path.isdir(str(BASE_DIR)+"/archives/"+nnid):
                        os.mkdir(str(BASE_DIR)+"/archives/"+nnid)
                    if len(api['images']['image']) > 4:
                        for url in miis:
                            #loop through every Mii URL in the json, then save
                            image = get(url["url"], verify=False)
                            #dirty fix for checking for the TGA format mii image
                            if url['type'] == "standard":
                                extension = ".tga"
                            else:
                                extension = ".png"
                            #compress image
                            image = Image.open(io.BytesIO(image.content))
                            img = io.BytesIO()
                            image.save(img, format="WEBP", quality=40)
                            img = img.getvalue()
                            file = open(str(BASE_DIR)+"/archives/"+nnid+"/"+url['type']+extension, "wb")
                            file.write(img)
                            file.close()
                    else:
                        #loop through every Mii URL in the json, then save
                        image = get(miis["url"], verify=False)
                        #dirty fix for checking for the TGA format mii image
                        if miis['type'] == "standard":
                            extension = ".tga"
                        else:
                            extension = ".png"
                        image = Image.open(io.BytesIO(image.content))
                        img = io.BytesIO()
                        image.save(img, format="WEBP", quality=40)
                        img = img.getvalue()
                        file = open(str(BASE_DIR)+"/archives/"+nnid+"/"+miis['type']+extension, "wb")
                        file.write(img)
                        file.close()

                    NintendoNetworkID.objects.create(nnid=nnid, mii_hash=api['images']['hash'], mii_data=api['data'], nickname=api['name'], pid=api['pid'], rank=(1800000000 - int(api['pid'])), owner=None, archived_on=now(), refreshed_on=now())
                    print("[AutoArchiver] Archived "+nnid+" (pid: "+str(i)+")!")
            except KeyboardInterrupt:
                print("[AutoArchiver] Stopping.")
                pid.truncate(0)
                pid.seek(0)
                pid.write(str(i))
                pid.close()
                os.remove("/tmp/nnid_scrapper_running")
        except OperationalError:
            os.remove("/tmp/nnid_scrapper_running")
            print("[AutoArchiver] Could not initialize!!!! Cause: DB is not initialized.")
    except:
        print("[AutoArchiver] Seems like I crashed. Sad moment.")
        pid.truncate(0)
        pid.seek(0)
        pid.write(str(i))
        pid.close()
        os.remove("/tmp/nnid_scrapper_running")
