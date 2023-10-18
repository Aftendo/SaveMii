from django.shortcuts import render
from miiapp.models import *
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse, Http404, HttpResponseRedirect, HttpResponse
from requests import get
from json import loads
from savemii.settings import BASE_DIR, NINTENDO_API_SECRET, NINTENDO_API_ID
from django.utils.timezone import now
from base64 import b64decode
from PIL import Image
import threading, xmltodict, shutil, os, io

print("Hi there! Checking if /archives/ exists....")
if os.path.isdir(str(BASE_DIR)+"/archives/"):
    print("It does!")
else:
    print("It doesn't. Creating directory.")
    os.mkdir(str(BASE_DIR)+"/archives/")


def auto_scrapper_thread():
    os.system("python3 auto_archiver.py")

if os.environ.get("SERVER_RUNNING") == "True":
    if  not os.path.exists("/tmp/nnid_scrapper_running"):
        scrapper_thread = threading.Thread(target=auto_scrapper_thread, daemon=True)
        scrapper_thread.start()
    else:
        print("[AutoArchiver] Seems like I'm already running. If I'm not, delete /tmp/nnid_scrapper_running")
else:
    print("[AutoArchiver] Server not running; not starting.")

# This is the actual NNID archiver code. The website is a wrapper for that only function.
def nnidArchiver(nnid: str, user, refresh):
    if not refresh:
        print("Archiving "+nnid+"!")
    else:
        print("Refreshing "+nnid+"!")
    # had the nnid been archived already?
    try:
        nnid_db = NintendoNetworkID.objects.get(nnid=nnid)
        if not refresh:
            return "This NNID has already been archived. If the NNID has been changed since its archival, please use the 'Refresh NNID' button."
        else:
            if (now()-nnid_db.refreshed_on).days < 1:
                return "This NNID has been refreshed today. Please try again tomorrow."
    except ObjectDoesNotExist:
        pass
    try:
        is_blocked = BlockedNNID.objects.get(nnid=nnid)
        return "This NNID cannot be archived because it has been blocked."
    except ObjectDoesNotExist:
        pass

    # use the nintendo network api
        
    #default headers, according to https://github.com/kinnay/NintendoClients/wiki/Account-Server
    headers = {
        "X-Nintendo-Client-ID": NINTENDO_API_ID,
        "X-Nintendo-Client-Secret": NINTENDO_API_SECRET
    }

    #get principal id (pid)
    url = "https://accountws.nintendo.net/v1/api/admin/mapped_ids"
    payload = {'input_type': 'user_id', 'output_type': 'pid', 'input': nnid}
    response = get(url, params=payload, headers=headers)
    pid = xmltodict.parse(response.text)['mapped_ids']['mapped_id']['out_id']

    if not pid:
        return "The NNID could not be found."

    #get mii data with pid
    url = "https://accountws.nintendo.net/v1/api/miis"
    payload = {'pids': pid}
    response = get(url, params=payload, headers=headers)
    if response.status_code == 404:
        return "The NNID was deleted."
     api = xmltodict.parse(response.text)['miis']['mii']

    try:
        api['images']['hash'] = api["images"]["image"][0]["url"].split("/")[-1].split("_")[0]
    except KeyError:
        api['images']['hash'] = api["images"]["image"]["url"].split("/")[-1].split("_")[0]
        
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
                image = Image.open(io.BytesIO(image.content))
                img = io.BytesIO()
                image.save(img, format="WEBP", quality=40)
                img = img.getvalue()
                file = open(str(BASE_DIR)+"/archives/"+nnid+"/"+url['type']+extension, "wb")
                file.write(img)
                file.close()
    else:
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
    if not user.is_authenticated:
        user = None
    if not refresh:
        NintendoNetworkID.objects.create(nnid=nnid, mii_hash=api['images']['hash'], mii_data=api['data'], nickname=api['name'], pid=api['pid'], rank=(1800000000 - int(api['pid'])), owner=user, archived_on=now(), refreshed_on=now(), is_auto_archived=False)
    else:
        nnid_db.mii_data = api['data']
        nnid_db.nickname = api['name']
        nnid_db.refreshed_on = now()
        nnid_db.refresher = user
        nnid_db.save()
    print("Archived/Refreshed "+nnid+"!")   


def index(request):
    count_of_nnid = NintendoNetworkID.objects.all().count()
    if not os.path.exists("/tmp/nnid_scrapper_running"):
        alive = False
    else: 
        alive = True
    return render(request, 'index.html', {"title": "Home", "count": count_of_nnid, "is_auto_running": alive})

def archive(request):
    if request.method == 'POST':
        if not request.POST.get('nnid'):
            return render(request, "archive.html", {"title": "Archive an NNID", "message": "You didn't put an NNID."})
        else:
            nnid = nnidArchiver(request.POST.get('nnid'), request.user, False)
            if nnid != None:
                return render(request, "archive.html", {"title": "Archive an NNID", "message": nnid})
            else:
                return render(request, "archive.html", {"title": "Archive an NNID", "success": True, "nnid": request.POST.get('nnid')})
    return render(request, 'archive.html', {"title": "Archive an NNID"})

def privacy(request):
    return render(request, 'privacy.html', {"title": "Privacy Policy"})

def qna(request):
    return render(request, 'qna.html', {"title": "QnA"})

def disconnect(request):
    if request.user.is_authenticated:
        logout(request)
        return HttpResponseRedirect("/")
    else:
        return HttpResponseRedirect("/")

def signin(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect("/")
    if request.method == 'POST':
        if not request.POST.get('username') or not request.POST.get('password'): 
            return render(request, "signin.html", {"title": "Sign In", "message": "All fields weren't filled."})
        else:
            user = authenticate(username=request.POST.get("username"), password=request.POST.get("password"))
            if user == None:
                return render(request, "signin.html", {"title": "Sign In", "message": "The username/password is incorrect."})
            else:
                login(request, user)
                return HttpResponseRedirect("/")
    return render(request, 'signin.html', {"title": "Sign In"})

def signup(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect("/")
    if request.method == 'POST':
        if not request.POST.get('username') or not request.POST.get('password') or not request.POST.get('cpassword'): 
            return render(request, "signup.html", {"title": "Sign Up", "message": "All fields weren't filled."})
        else:
            if request.POST.get("password") != request.POST.get("cpassword"):
                return render(request, "signup.html", {"title": "Sign Up", "message": "Passwords don't match."})
            if request.POST.get('username') == "Anonymous" or request.POST.get('username') == "Auto Archiver":
                return render(request, "signup.html", {"title": "Sign Up", "message": "You cannot use that name."})
            try:
                conflict = User.objects.get(username=request.POST.get("username"))
                return render(request, "signup.html", {"title": "Sign Up", "message": "A user with the same username already exists."})
            except ObjectDoesNotExist:
                pass
            user = User.objects.create_user(request.POST.get("username"), None, request.POST.get("password"))
            user.save()
            return HttpResponseRedirect("/signin")
    return render(request, 'signup.html', {"title": "Sign Up"})

def randomNNID(request):
    nnid = NintendoNetworkID.objects.order_by('?')[0]
    return HttpResponseRedirect("/nnid/"+nnid.nnid)

def favorite(request, nnid):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    try:
        nnid_db = NintendoNetworkID.objects.get(nnid=nnid)
    except ObjectDoesNotExist:
        raise Http404()
    try:
        favorite = Favorite.objects.get(target=nnid_db, source=request.user)
        favorite.delete()
        return HttpResponseRedirect("/favorites")
    except ObjectDoesNotExist:
        Favorite.objects.create(target=nnid_db, source=request.user)
        return HttpResponseRedirect("/nnid/"+nnid_db.nnid)

def viewNNID(request, nnid):
    try:
        nnid_db = NintendoNetworkID.objects.get(nnid=nnid)
    except ObjectDoesNotExist:
        raise Http404()
    if request.user.is_authenticated:
        try:
            favorite = Favorite.objects.get(target=nnid_db, source=request.user)
            is_fav = True
        except ObjectDoesNotExist:
            is_fav = False
    else:
        is_fav = False
    if nnid_db.owner == None  and nnid_db.is_auto_archived:
        owner = "Auto Archiver"
    elif nnid_db.owner == None:
        owner = "Anonymous"
    else:
        owner = nnid_db.owner
    return render(request, "viewnnid.html", {"title": nnid, "nnid": nnid_db, "owner": owner, "is_fav": is_fav})

def search(request):
    if request.method == 'POST':
        if not request.POST.get('search'):
            return HttpResponseRedirect("/")
        nnids = NintendoNetworkID.objects.filter(nnid__icontains=request.POST.get('search')).order_by("?")
        return render(request, "search.html", {"title": "Search", "results": nnids, "query": request.POST.get('search')})
    else:
        return HttpResponseRedirect("/")
    
def complaint(request, nnid):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    try:
        nnid = NintendoNetworkID.objects.get(nnid=nnid)
    except ObjectDoesNotExist:
        raise Http404()
    if request.method == 'POST':
        if not request.POST.get('complaint'):
            return render(request, "complaint.html", {"title": "Send a complaint", "message": "All fields weren't filled.", "nnid": nnid.nnid})
        Complaint.objects.create(target=nnid, content=request.POST.get('complaint'), author=request.user)
        return render(request, "complaint.html", {"title": "Send a complaint", "success": True, "nnid": nnid.nnid})
    return render(request, "complaint.html", {"title": "Send a complaint", "nnid": nnid.nnid})

def refresh(request, nnid):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    result = nnidArchiver(nnid, request.user, True)
    if result != None:
        return render(request, "refresh.html", {"title": "Refresh "+nnid, "message": result, "nnid":nnid})
    else:
        return render(request, "refresh.html", {"title": "Refresh "+nnid, "success": True, "nnid":nnid})
    

def owned(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    nnids = NintendoNetworkID.objects.filter(owner=request.user).order_by("?")
    return render(request, "owned.html", {"title": "NNIDs you've archived", "results": nnids})

def favorites(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    nnids = Favorite.objects.filter(source=request.user).order_by("?")
    return render(request, "favorites.html", {"title": "NNIDs you've put as favorite", "results": nnids})

def miniadmin(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    if not request.user.is_staff:
        return HttpResponseRedirect("/")
    return render(request, "admin/miniadmin.html", {"title": "Mini admin panel"})

def complaints(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    if not request.user.is_staff:
        return HttpResponseRedirect("/")
    complaint = Complaint.objects.all()
    if request.method == 'POST':
        if not request.POST.get('complaint'):
            return HttpResponse("missing complaint id")
        try:
            selected = Complaint.objects.get(id=request.POST.get('complaint'))
        except ObjectDoesNotExist:
            return HttpResponse("complaint not found sorry")
        selected.delete()
    return render(request, "admin/complaints.html", {"title": "Complaints list", "complaints": complaint})

def delete(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    if not request.user.is_staff:
        return HttpResponseRedirect("/")
    if request.method == 'POST':
        if not request.POST.get('nnid'):
            return HttpResponse("missing nnid")
        try:
            nnid = NintendoNetworkID.objects.get(nnid=request.POST.get('nnid'))
        except ObjectDoesNotExist:
            return HttpResponse("nnid not found sorry")
        if not os.path.isdir(str(BASE_DIR)+"/archives/"+nnid.nnid):
            pass
        else:
            shutil.rmtree(str(BASE_DIR)+"/archives/"+nnid.nnid)
        nnid.delete()
        if request.POST.get('blocklist'):
            BlockedNNID.objects.create(nnid=request.POST.get('nnid'))
        return HttpResponse("deleted")
    return render(request, "admin/delete.html", {"title": "Delete an NNID"})

def api(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    return render(request, "api.html", {"title": "API"})

def miiImage(request, hash, type):
    try:
        nnid = NintendoNetworkID.objects.get(mii_hash=hash)
    except ObjectDoesNotExist:
        return JsonResponse({"error": True, "message": "NNID corresponding to Hash not found"}, status=404)
    if type=="standard":
        extension = ".tga"
        content_type = "image/x-tga"
    else:
        extension = ".png"
        content_type = "image/png"
    path = str(BASE_DIR)+"/archives/"+nnid.nnid+"/"+type+extension
    if not os.path.isfile(path):
        return JsonResponse({"error": True, "message": "Image not found"}, status=400)
    image = open(path, "rb")
    return HttpResponse(image.read(), content_type=content_type)

def miiData(request, hash):
    try:
        nnid = NintendoNetworkID.objects.get(mii_hash=hash)
    except ObjectDoesNotExist:
        return JsonResponse({"error": True, "message": "NNID corresponding to Hash not found"}, status=404)
    mii = b64decode(nnid.mii_data)
    response = HttpResponse(mii)
    response['Content-Disposition'] = 'attachement; filename="'+nnid.nnid+'.mii"'
    return response

def getNNIDInfo(request):
    if not request.GET.get("nnid"):
        return JsonResponse({"error": False, "message": "Missing parameters"})
    try:
        nnid = NintendoNetworkID.objects.get(nnid=request.GET.get("nnid"))
    except ObjectDoesNotExist:
        return JsonResponse({"error": True, "message": "NNID not found/not archived"}, status=404)
    if nnid.owner == None and nnid.is_auto_archived:
        owner = "Auto Archiver"
    elif nnid.owner == None:
        owner = None
    else:
        owner = nnid.owner.username
    if nnid.refresher == None:
        refresher = None
    else:
        refresher = nnid.refresher.username
    return JsonResponse({"error": False, "nnid": {"nnid": nnid.nnid, "mii": {"nickname": nnid.nickname, "hash": nnid.mii_hash, "data": nnid.mii_data}, "pid": nnid.pid, "rank": nnid.rank, "savemii": {"owner": owner, "refresher": refresher, "archived_on": nnid.archived_on, "refreshed_on": nnid.refreshed_on, "is_auto_archived": nnid.is_auto_archived}}})

def getHash(request):
    if not request.GET.get("nnid"):
        return JsonResponse({"error": False, "message": "Missing parameters"})
    try:
        nnid = NintendoNetworkID.objects.get(nnid=request.GET.get("nnid"))
    except ObjectDoesNotExist:
        return JsonResponse({"error": True, "message": "NNID not found/not archived"}, status=404)
    return HttpResponse(nnid.mii_hash)

def archived(request):
    return HttpResponse(NintendoNetworkID.objects.all().count())

def err404(request, exception):
    return render(request, "404.html", {"title": "404"})
