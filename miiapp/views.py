from django.shortcuts import render
from miiapp.models import *
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse, Http404, HttpResponseRedirect, HttpResponse
from requests import get
from json import loads
import os
import shutil
from savemii.settings import BASE_DIR
from django.utils.timezone import now
from base64 import b64decode
from binascii import hexlify
import xmltodict

print("Hi there! Checking if /archives/ exists....")
if os.path.isdir(str(BASE_DIR)+"/archives/"):
    print("It does!")
else:
    print("It doesn't. Creating directory.")
    os.mkdir(str(BASE_DIR)+"/archives/")
# This is the actual NNID archiver code. The website is a wrapper for that only function.
def nnidArchiver(nnid: str, user, refresh):
    if not refresh:
        print("Archiving "+nnid+"!")
    else:
        print("Refreshing "+nnid+"!")
    # had the nnid been archived already?
    try:
        conflict = NintendoNetworkID.objects.get(nnid=nnid)
        if not refresh:
            return "This NNID has already been archived. If the NNID has been changed since its archival, please use the 'Refresh NNID' button."
        else:
            if (now()-conflict.refreshed_on).days < 1:
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
        "X-Nintendo-Client-ID": "a2efa818a34fa16b8afbc8a74eba3eda",
        "X-Nintendo-Client-Secret": "c91cdb5658bd4954ade78533a339cf9a"
    }

    #get principal id (pid)
    url = "https://accountws.nintendo.net/v1/api/admin/mapped_ids"
    payload = {'input_type': 'user_id', 'output_type': 'pid', 'input': nnid}
    response = get(url, params=payload, headers=headers)
    pid = xmltodict.parse(response.text)['mapped_ids']['mapped_id']['out_id']

    #get mii data with pid
    url = "https://accountws.nintendo.net/v1/api/miis"
    payload = {'pids': pid}
    response = get(url, params=payload, headers=headers)
    api = xmltodict.parse(response.text)['miis']['mii']

    api['images']['hash'] = api["images"]["image"][0]["url"].split("/")[-1].split("_")[0]

    # if message (error) key exists, return it
    if "message" in api:
        return api['message']
    #else, continue with the archiving process
    api['data'] = hexlify(b64decode(api['data'])).decode()
    #WARNING: POORLY WRITTEN CODE AHEAD!!
    # save mii images
    miis = api['images']['image']
    if not os.path.isdir(str(BASE_DIR)+"/archives/"+nnid):
        os.mkdir(str(BASE_DIR)+"/archives/"+nnid)
    for url in miis:
        #loop through every Mii URL in the json, then save
        image = get(url["url"], verify=False)
        #dirty fix for checking for the TGA format mii image
        if url['type'] == "standard":
            extension = ".tga"
        else:
            extension = ".png"
        file = open(str(BASE_DIR)+"/archives/"+nnid+"/"+url['type']+extension, "wb")
        file.write(image.content)
        file.close()
    if not user.is_authenticated:
        user = None
    if not refresh:
        NintendoNetworkID.objects.create(nnid=nnid, mii_hash=api['images']['hash'], mii_data=api['data'], nickname=api['name'], pid=api['pid'], owner=user)     
    else:
        conflict.mii_data = api['data']
        conflict.nickname = api['name']
        conflict.refreshed_on = now()
        conflict.refresher = user
        conflict.save()
    print("Archived/Refreshed "+nnid+"!")   


def index(request):
    count_of_nnid = NintendoNetworkID.objects.all().count()
    return render(request, 'index.html', {"title": "Home", "count": count_of_nnid})

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
            if request.POST.get('username') == "Anonymous":
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
    if nnid_db.owner == None:
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

def getNNIDInfo(request):
    if not request.GET.get("nnid"):
        return JsonResponse({"error": False, "message": "Missing parameters"})
    try:
        nnid = NintendoNetworkID.objects.get(nnid=request.GET.get("nnid"))
    except ObjectDoesNotExist:
        return JsonResponse({"error": True, "message": "NNID not found/not archived"}, status=404)
    if nnid.owner == None:
        owner = None
    else:
        owner = nnid.owner.username
    if nnid.refresher == None:
        refresher = None
    else:
        refresher = nnid.refresher.username
    return JsonResponse({"error": False, "nnid": {"nnid": nnid.nnid, "mii": {"nickname": nnid.nickname, "hash": nnid.mii_hash, "data": nnid.mii_data}, "pid": nnid.pid, "savemii": {"owner": owner, "refresher": refresher, "archived_on": nnid.archived_on, "refreshed_on": nnid.refreshed_on}}})

def getHash(request):
    if not request.GET.get("nnid"):
        return JsonResponse({"error": False, "message": "Missing parameters"})
    try:
        nnid = NintendoNetworkID.objects.get(nnid=request.GET.get("nnid"))
    except ObjectDoesNotExist:
        return JsonResponse({"error": True, "message": "NNID not found/not archived"}, status=404)
    return HttpResponse(nnid.mii_hash)

def err404(request, exception):
    return render(request, "404.html", {"title": "404"})
